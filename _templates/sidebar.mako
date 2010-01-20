<div id="right_sidebar">
  <div id="contact">
  <h3>Contact</h3>
  <p>
  <a href="http://www.google.com/profiles/bob.ippolito">Bob Ippolito</a><br />
  <small>
  Co-founder and CTO of <a href="http://www.mochimedia.com/">Mochi Media</a>, open source python/erlang hacker
  </small>
  </p>
  </div>
  <div id="blog_post_list">
  <h3>Latest blog posts</h3>
  <ul>
% for post in bf.posts[:5]:
    <li><a href="${post.path}">${post.title}</a></li>
% endfor
  </ul>
 
    <div id="subscribe">
        <p>Subscribe via <a href="/feed/">RSS</a></p>
        <div class="clear"></div>
    </div>

  </div>
  <div id="on_twitter">
    <h3>On Twitter</h3>
    <div id="blogofile_tweets"></div>
    <a href="http://search.twitter.com/search?q=etrepum" style="float: right">See more tweets</a>
    <div style="clear: both">&nbsp;</div>
  </div>
  <div id="categories">
    <h3>Categories</h3>
    <ul>
% for category, num_posts in bf.all_categories:
     <li><a href="${category.path}">${category}</a><!-- (<a href="${category.path}/feed/">rss</a>)--> (${num_posts})</li>
% endfor
    </ul>
  </div> 
  <div id="archives">
    <h3>Archives</h3>
    <ul>
% for link, name, num_posts in bf.archive_links:
      <li><a href="/${bf.util.blog_path_helper(bf.config.blog_path,link)}/1" title="${name}">${name}</a>&nbsp;(${num_posts})</li>
% endfor
    </ul>
  </div>

</div>
