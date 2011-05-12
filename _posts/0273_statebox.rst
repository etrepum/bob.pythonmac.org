---
categories: mochi, erlang
date: 2011/05/09 09:00:00
permalink: http://bob.pythonmac.org/archives/2011/03/17/statebox/
tags: riak, statebox, opensource, erlang
title: statebox, an eventually consistent data model for Erlang (and Riak)
author: bob
---

*Cross-posted from the Mochi Labs blog*: `statebox, an eventually consistent data model for Erlang (and Riak) <http://labs.mochimedia.com/archive/2011/05/08/statebox/>`_.

A few weeks ago when I was on call at work I was chasing down a bug in
friendwad [#]_ and I realized that we had made a big mistake. The data
model was broken, it could only work with transactions but we were using
`Riak`_. The original prototype was built with Mnesia, which would've
been able to satisfy this constraint, but when it was refactored for
an eventually consistent data model it just wasn't correct anymore.
Given just a little bit of concurrency, such as a popular user, it would
produce inconsistent data. Soon after this discovery, I found another
service built with the same invalid premise and I also realized
that a general solution to this problem would allow us to migrate several
applications from Mnesia to Riak.

When you choose an eventually consistent data store you're
prioritizing availability and partition tolerance over consistency,
but this doesn't mean your application has to be inconsistent. What it
does mean is that you have to move your conflict resolution from
writes to reads. `Riak`_ does almost all of the hard work for you [#]_,
but if it's not acceptable to discard some writes then you will have to
set ``allow_mult`` to ``true`` on your bucket(s) and handle siblings
[#]_ from your application. In some cases, this might be trivial.
For example, if you have a set and only support adding to that set,
then a merge operation is just the union of those two sets.

`statebox`_ is my solution to this problem. It bundles the value with
repeatable operations [#]_ and provides a means to automatically
resolve conflicts. Usage of statebox feels much more declarative
than imperative. Instead of modifying the values yourself, you
provide statebox with a list of operations and it will apply them
to create a new statebox. This is necessary because it may apply
this operation again at a later time when resolving a conflict between
siblings on read.

Design goals (and non-goals):

* The intended use case is for data structures such as dictionaries
  and sets
* Direct support for counters is not required
* Applications must be able to control the growth of a statebox so that
  it does not grow indefinitely over time
* The implementation need not support platforms other than Erlang and
  the data does not need to be portable to nodes that do not share
  code
* It should be easy to use with Riak, but not be dependent on it
  (clear separation of concerns)
* Must be comprehensively tested, mistakes at this level are very expensive
* It is ok to require that the servers' clocks are in sync with NTP
  (but it should be aware that timestamps can be in the future or past)

Here's what typical statebox usage looks like for a trivial
application (note: Riak metadata is not merged [#]_). In this case we
are storing an orddict in our statebox, and this orddict has the keys
``following`` and ``followers``.

.. class:: erlang

::

    -module(friends).
    -export([add_friend/2, get_friends/1]).

    -define(BUCKET, <<"friends">>).
    -define(STATEBOX_MAX_QUEUE, 16).     %% Cap on max event queue of statebox
    -define(STATEBOX_EXPIRE_MS, 300000). %% Expire events older than 5 minutes
    -define(RIAK_HOST, "127.0.0.1").
    -define(RIAK_PORT, 8087).

    -type user_id() :: atom().
    -type orddict(T) :: [T].
    -type ordsets(T) :: [T].
    -type friend_pair() :: {followers, ordsets(user_id())} |
                           {following, ordsets(user_id())}.

    -spec add_friend(user_id(), user_id()) -> ok.
    add_friend(FollowerId, FolloweeId) ->
        statebox_riak:apply_bucket_ops(
        ?BUCKET,
        [{[friend_id_to_key(FollowerId)],
              statebox_orddict:f_union(following, [FolloweeId])},
         {[friend_id_to_key(FolloweeId)],
              statebox_orddict:f_union(followers, [FollowerId])}],
        connect()).

    -spec get_friends(user_id()) -> [] | orddict(friend_pair()).
    get_friends(Id) ->
        statebox_riak:get_value(?BUCKET, friend_id_to_key(Id), connect()).


    %% Internal API

    connect() ->
        {ok, Pid} = riakc_pb_client:start_link(?RIAK_HOST, ?RIAK_PORT),
        connect(Pid).

    connect(Pid) ->
        statebox_riak:new([{riakc_pb_client, Pid},
                           {max_queue, ?STATEBOX_MAX_QUEUE},
                           {expire_ms, ?STATEBOX_EXPIRE_MS},
                           {from_values, fun statebox_orddict:from_values/1}]).

    friend_id_to_key(FriendId) when is_atom(FriendId) ->
        %% NOTE: You shouldn't use atoms for this purpose, but it makes the
        %% example easier to read!
        atom_to_binary(FriendId, utf8).


To show how this works a bit more clearly, we'll use the following
sequence of operations:

.. class:: light erlang

::

   add_friend(alice, bob),       %% AB
   add_friend(bob, alice),       %% BA
   add_friend(alice, charlie).   %% AC

Each of these add_friend calls can be broken up into four separate
atomic operations, demonstrated in this pseudocode:

.. class:: light erlang

::

   %% add_friend(alice, bob)
   Alice = get(alice),
   put(update(Alice, following, [bob])),
   Bob = get(bob),
   put(update(Bob, followers, [alice])).

Realistically, these operations may happen with some concurrency and
cause conflict. For demonstration purposes we will have *AB* happen
concurrently with *BA* and the conflict will be resolved during *AC*.
For simplicity, I'll only show the operations that modify the key for
``alice``.

.. class:: light erlang

::

   AB = get(alice),                              %% AB (Timestamp: 1)
   BA = get(alice),                              %% BA (Timestamp: 2)
   put(update(AB, following, [bob])),            %% AB (Timestamp: 3)
   put(update(BA, followers, [bob])),            %% BA (Timestamp: 4)
   AC = get(alice),                              %% AC (Timestamp: 5)
   put(update(AC, following, [charlie])).        %% AC (Timestamp: 6)

Timestamp 1:
    There is no data for ``alice`` in Riak yet, so
    ``statebox_riak:from_values([])`` is called and we get a statebox
    with an empty orddict.
   

.. class:: light erlang

::

    Value = [],
    Queue = [].

Timestamp 2:
    There is no data for ``alice`` in Riak yet, so
    ``statebox_riak:from_values([])`` is called and we get a statebox
    with an empty orddict.

.. class:: light erlang

::

   Value = [],
   Queue = [].


Timestamp 3:
    Put the updated *AB* statebox to Riak with the updated value.

.. class:: light erlang

::

    Value = [{following, [bob]}],
    Queue = [{3, {fun op_union/2, following, [bob]}}].

Timestamp 4:
   Put the updated *BA* statebox to Riak with the updated value. Note
   that this will be a sibling of the value stored by *AB*.

.. class:: light erlang

::

   Value = [{followers, [bob]}],
   Queue = [{4, {fun op_union/2, followers, [bob]}}].

Timestamp 5:
    Uh oh, there are two stateboxes in Riak now... so
    ``statebox_riak:from_values([AB, BA])`` is called. This will apply
    all of the operations from both of the event queues to one of the
    current values and we will get a single statebox as a result.


.. class:: light erlang

::

   Value = [{followers, [bob]},
            {following, [bob]}],
   Queue = [{3, {fun op_union/2, following, [bob]}},
            {4, {fun op_union/2, followers, [bob]}}].


Timestamp 6:
    Put the updated *AC* statebox to Riak. This will resolve siblings
    created at Timestamp 3 by *BA*.

.. class:: light erlang

::

    Value = [{followers, [bob]},
             {following, [bob, charlie]}],
    Queue = [{3, {fun op_union/2, following, [bob]}},
             {4, {fun op_union/2, followers, [bob]}},
             {6, {fun op_union/2, following, [charlie]}}].

Well, that's about it! ``alice`` is following both ``bob`` and
``charlie`` despite the concurrency. No locks were harmed during this
experiment, and we've arrived at eventual consistency by using
`statebox_riak`_, `statebox`_, and `Riak`_ without having to write any
conflict resolution code of our own.

.. [#] friendwad manages our social graph for Mochi Social and MochiGames.
       It is also evidence that naming things is a hard problem in
       computer science.
.. [#] See Basho's articles on `Why Vector Clocks are Easy`_ and
       `Why Vector Clocks are Hard`_.
.. [#] When multiple writes happen to the same place and they have
       branching history, you'll get multiple values back on read.
       These are called siblings in `Riak`_.
.. [#] An operation ``F`` is repeatable if and only if ``F(V) = F(F(V))``.
       You could also call this an `idempotent unary operation`_.
.. [#] The default conflict resolution algorithm in statebox_riak
       chooses metadata from one sibling arbitrarily. If you use
       metadata, you'll need to come up with a clever way to merge it
       (such as putting it in the statebox and specifying a custom
       ``resolve_metadatas`` in your call to ``statebox_riak:new/1``).

.. _`statebox`: http://github.com/mochi/statebox
.. _`statebox_riak`: http://github.com/mochi/statebox_riak
.. _`Riak`: http://www.basho.com/products_riak_overview.php
.. _`Why Vector Clocks are Easy`: http://blog.basho.com/2010/01/29/why-vector-clocks-are-easy/
.. _`Why Vector Clocks are Hard`: http://blog.basho.com/2010/04/05/why-vector-clocks-are-hard/
.. _`idempotent unary operation`: http://en.wikipedia.org/wiki/Idempotence#Unary_operation
