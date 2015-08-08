<?xml version="1.0" encoding="UTF-8"?>
<!-- 
     Author of this stylesheet: Jonathan Cross (2007)
     Inspiration: Google Sitmaps Stylesheets (GSStylesheets)
                  Project Home: http://sourceforge.net/projects/gstoolbox
                  Copyright (c) 2005 Baccou Bonneville SARL (http://www.baccoubonneville.com)
                  License http://www.gnu.org/copyleft/lesser.html GNU/LGPL
-->
<xsl:stylesheet version="1.0" 
                xmlns:html="http://www.w3.org/1999/xhtml"
                xmlns:sitemap="http://www.sitemaps.org/schemas/sitemap/0.9"
                xmlns:image="http://www.google.com/schemas/sitemap-image/1.1"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:jcd="http://pics.jonathancross.com">
  <xsl:output method="html" version="1.0" encoding="UTF-8"/>

  <!-- Base node -->
  <xsl:variable name="base" select="/sitemap:urlset/sitemap:url[sitemap:priority='1.0']"/>
  <!-- Get the URL. -->
  <xsl:variable name="baseURL" select="$base/sitemap:loc"/>
  <!-- simplified version -->
  <xsl:variable name="simpleWebsiteURL" select="substring-before(substring-after($baseURL,'http://'),'/')"/>
  
  <xsl:template match="/">
    <html>
      <head>  
        <title>Sitemap for: <xsl:value-of select="$simpleWebsiteURL"/>.</title>
        <link href="jcdsee/jcdsee.css" type="text/css" rel="stylesheet"/>
        <!--
        <script src="jcdsee/prototype.js" type="text/javascript"></script>
        <script src="jcdsee/scriptaculous/scriptaculous.js" type="text/javascript"></script>
        -->
        <xsl:comment><![CDATA[[if lt IE 8]>  <script src='jcdsee/IE8/IE8.js' type='text/javascript'></script>  <![endif]]]></xsl:comment>
        <style type="text/css">
          body {font-family:arial,helvetica,sans-serif;margin: 15px;}
          h1 {color:#888;margin:0;}
          h1 a {text-decoration:none;color:#222;}
          h1 a:hover {color:#777;}
          h5 {color: #666;font-weight:normal;margin-top:0.5em;margin-bottom:1em;}
          #file_list a {color:#66a;}
          #file_list a:hover {color:#00f;text-decoration:underline;}
          tr:hover {background-color:#e3e3ff;color:#000;}
          tr:hover td div {color:#333;}
          tr:hover .date,
          tr:hover .imgCount {color:#333;}
          td.date {white-space:nowrap;border-left:1px solid #ccc;text-align:center;color:#888;}
          th {white-space:nowrap;font-size:11px;background-color:#aaa;color:black;}
          th.date {border-left:1px solid #ccc;text-align:center;}
          A {text-decoration:none;cursor:pointer;}
          img {border:none;}
          .tabPosition {top:1pt;position:relative;z-index:1;}
          .tabR,.tabL {padding:4px 1px 0px 8px;}
          .tabR {padding-right:4px;}
          a.tabR img {opacity:0.4;}
          a.tabR:after {
            content: "."; 
            visibility: hidden;
          }
          a.tabR:hover img {opacity:1;}
          .openTab .tabL {background:url('jcdsee/icon_tab_bg.png') no-repeat top left;}
          .openTab .tabR {background:url('jcdsee/icon_tab_bg.png') no-repeat top right;}
          .openTab .imgCount {display:inline;top:-1px;position:relative;margin-left:7px;font-size:0.8em;color:#aaa;}
          .openTab .tabContent {display:block;background-color:#d5d5ff;border:1px solid #99f;padding:1pt 4px 4px 7px;}
          .tabContent,.imgCount {display:none;overflow:hidden;}
          /* JCDSee 2 styles below. */
          table#file_list {
            font-size: 12px;
            max-width: 700px;
          }
        </style>       
      </head> 
      <body id="mode-list">
        <h1>Sitemap for: <a href="{$baseURL}"><xsl:value-of select="$simpleWebsiteURL"/></a></h1>
        <h5>BUILT: <xsl:value-of select="sitemap:urlset/@jcd:date"/> <code>  </code> (<xsl:value-of select="count(sitemap:urlset/sitemap:url)"/> URLs, Size: <xsl:value-of select="$base/@jcd:dsize"/> / 285GB)</h5>          
        <xsl:call-template name="sitemapTable"/>
      </body>
    </html>
  </xsl:template>     
 
  <xsl:template name="sitemapTable">
    <script type="text/javascript">
      var preloadBG=new Image();
      preloadBG.src="jcdsee/icon_tab_bg.png";
      var buttonImgOpen=new Image();
      buttonImgOpen.src="jcdsee/icon_tab_open.png";
      var buttonImgClose=new Image();
      buttonImgClose.src="jcdsee/icon_tab_close.png";
      var curTab,button,buttonImg,tabContent,curTabHeight;
      var animStep=7;
      var animTimer=150;
      var shrinkHeight=18;
      var expandHeight=36;
      function expandTab(id) {
        if (document.getElementById) {
          curTab=document.getElementById('TAB'+id);
          button=curTab.getElementsByTagName('a')[1];
          buttonImg=button.firstChild;
          tabContent=curTab.getElementsByTagName('div')[1];
          //alert('height:'+tabContent.offsetHeight)
          if (curTab.className.indexOf("openTab") != -1) {
            var initHeight=curTab.offsetHeight;
            var isShrink=1;
            var initAnimTimer=0;
            //alert('shrinkHeight was:'+shrinkHeight+'\nNEW shrinkHeight:'+tabContent.offsetHeight)
            tabAnimation(initHeight,isShrink,initAnimTimer);
            curTab.className="l";
            buttonImg.src=buttonImgOpen.src;
          }else{
            var initHeight=curTab.offsetHeight;
            var isShrink=0;
            var initAnimTimer=0;
            //alert('expandHeight was:'+expandHeight+'\nNEW expandHeight:'+tabContent.offsetHeight)
            tabAnimation(initHeight,isShrink,initAnimTimer);
            //tab.className="l openTab";
          }
        }
      }
      function tabAnimation(height,isShrink,animTimerInit) {
        if (isShrink) {
          if (height &gt;= shrinkHeight) {
            //alert('shrinking height='+height)
            curTab.style.height=height+"px"
            height-=animStep;
            setTimeout("tabAnimation("+height+","+isShrink+",animTimer)", animTimerInit);
          }
        }else{
          if (height &lt;= expandHeight) {
            curTab.style.height=height+"px"
            height+=animStep;
            setTimeout("tabAnimation("+height+","+isShrink+",animTimer)", animTimerInit);
          }else{
            //alert('finished expanding. height='+height)
            curTab.className="l openTab";
            buttonImg.src=buttonImgClose.src;
          }
        }
      }
    </script>
    <table id="file_list" cellpadding="4" cellspacing="0" border="0">
      <tbody>
        <tr>
          <th width="100%">URL</th>
          <th class="date">CREATED</th>
          <th class="date">MODIFIED</th>
        </tr>
        <xsl:apply-templates select="sitemap:urlset/sitemap:url">
          <xsl:sort select="sitemap:loc"/>
        </xsl:apply-templates>
      </tbody>
    </table>  
  </xsl:template>    
  
  <xsl:template name="parseItemName">
    <xsl:param name="itemName"/>
    <xsl:param name="indent" select="10"/>
    <xsl:choose>
      <xsl:when test="contains($itemName,'/')">
        <xsl:call-template name="parseItemName">
          <xsl:with-param name="itemName" select="substring-after($itemName,'/')"/>
          <xsl:with-param name="indent" select="$indent + 25"/>
        </xsl:call-template>
      </xsl:when>
      <xsl:otherwise>
        <xsl:value-of select="$indent"/>
        <xsl:call-template name="parseItemCreatedDate">
          <xsl:with-param name="itemName" select="$itemName"/>
        </xsl:call-template>
      </xsl:otherwise>
    </xsl:choose>    
  </xsl:template>    
  
  <!-- Parse %20, '-' and '_' into real spaces -->
  <xsl:template name="getItemTitle">
    <xsl:param name="itemName"/>
    <xsl:choose>
      <xsl:when test="contains($itemName,'%20')">
        <xsl:call-template name="getItemTitle">
          <xsl:with-param name="itemName" select="concat(substring-before($itemName,'%20'),' ',substring-after($itemName,'%20'))"/>
        </xsl:call-template>
      </xsl:when>
      <xsl:otherwise>
        <xsl:value-of select="translate($itemName,'_-','  ')"/>
      </xsl:otherwise>
    </xsl:choose>    
  </xsl:template>    
  
  <xsl:template name="parseItemCreatedDate">
    <xsl:param name="itemName"/>
    <xsl:variable name="testDate" select="substring-before($itemName,'_')"/>
    <xsl:choose>
      <xsl:when test="translate($testDate,'0123456789','xxxxxxxxxx') = 'xxxx-xx-xx'">
        <xsl:text>[0]</xsl:text>
        <xsl:value-of select="$testDate"/>
        <xsl:text>[1]</xsl:text>
       <xsl:call-template name="getItemTitle">
          <xsl:with-param name="itemName" select="substring-after($itemName,concat($testDate,'_'))"/>
       </xsl:call-template>
      </xsl:when>
      <xsl:when test="translate($itemName,'0123456789','xxxxxxxxxx') = 'xxxx'">
        <xsl:text>[0]</xsl:text>
        <xsl:value-of select="$itemName"/>
        <xsl:text>[1]</xsl:text>
        <xsl:call-template name="getItemTitle">
          <xsl:with-param name="itemName" select="$itemName"/>
        </xsl:call-template>
      </xsl:when>
      <xsl:otherwise>
        <xsl:text>[0]</xsl:text>
        <xsl:text>-</xsl:text>
        <xsl:text>[1]</xsl:text>
        <xsl:call-template name="getItemTitle">
          <xsl:with-param name="itemName" select="$itemName"/>
        </xsl:call-template>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>    
  
  <!-- normal URL -->  
  <xsl:template match="sitemap:url">
    <xsl:variable name="URL"><xsl:value-of select="sitemap:loc"/></xsl:variable>
    <xsl:variable name="relURL"><xsl:value-of select="substring-after($URL,$baseURL)"/></xsl:variable>
    <!-- build $itemName -->
    <xsl:variable name="len" select="string-length($relURL)"/>
    <xsl:variable name="lastChar" select="substring($relURL,$len)"/>
    <xsl:variable name="itemArray">
      <xsl:call-template name="parseItemName">
        <xsl:with-param name="itemName">
          <xsl:choose>
           <xsl:when test="$lastChar='/'">
             <!-- FOLDER (strip off the trailing '/' AND initial '/') -->
             <xsl:value-of select="substring($relURL,1,($len -1))"/>
           </xsl:when>
          <xsl:when test="$relURL=''">
            <!-- website root -->
            <xsl:value-of select="sitemap:lastmod"/>_HOME PAGE
          </xsl:when>
           <xsl:otherwise>
             <!-- HTML file (only strip off initial '/') -->
             <xsl:value-of select="substring($relURL,1)"/>
           </xsl:otherwise>
          </xsl:choose>
        </xsl:with-param>
      </xsl:call-template>
    </xsl:variable>
    <!-- Break apart the $itemArray into variables -->
    <xsl:variable name="itemIndent" select="substring-before($itemArray,'[0]')"/>
    <xsl:variable name="itemCreatedDate" select="substring-before(substring-after($itemArray,'[0]'),'[1]')"/>
    <xsl:variable name="itemTitle" select="substring-after($itemArray,'[1]')"/>
    <xsl:variable name="i" select="position()"/>
<xsl:text>
</xsl:text>
    <!-- do onmouseover in javascript -->
    <tr title="{jcd:desc}">
      <td id="TAB{$i}" class="l" style="padding-left:{$itemIndent}px;" valign="top"><!-- T,R,B,L -->
        <div class="tabPosition">
          <a href="{sitemap:loc}" class="tabL">
            <xsl:value-of select="$itemTitle"/>
          </a>
          <!-- Hide the description for pages that have none.  Enable later for images but no desc? -->
          <xsl:if test="jcd:desc">
            <a class="tabR" onclick="expandTab('{$i}')">
              <img src="jcdsee/icon_tab_open.png" alt="More info." />
            </a>
          </xsl:if>
          <span class="imgCount">
            <xsl:if test="@jcd:imgs &gt; 0">
              <xsl:value-of select="@jcd:imgs"/> images,
            </xsl:if>
            <xsl:value-of select="@jcd:dsize"/>
          </span>
        </div>
        <div class="tabContent"><xsl:value-of select="jcd:desc"/></div>
      </td>
      <td class="date">
        <xsl:value-of select="$itemCreatedDate"/>
      </td>
      <td class="date"><xsl:value-of select="sitemap:lastmod"/></td>
    </tr>
  </xsl:template>
    
</xsl:stylesheet>
