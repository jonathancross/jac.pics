<?xml version="1.0" encoding="UTF-8"?>
<!--
  JCDSee 2.1.1+
  XSL code used to parse folder information from sitemap.xml file.
  This is called from the CGI script to get site-wide meta data.
-->
<xsl:stylesheet version="1.0" 
                xmlns:html="http://www.w3.org/1999/xhtml"
                xmlns:sitemap="http://www.sitemaps.org/schemas/sitemap/0.9"
                xmlns:image="http://www.google.com/schemas/sitemap-image/1.1"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:jcd="http://pics.jonathancross.com">
  <xsl:output omit-xml-declaration="yes" indent="no"/>
  <xsl:variable name="BASE">http://pics.jonathancross.com</xsl:variable>

  <!-- Name of the data item we want to retrieve:
     1. urlFragment : retrieve a list of case-insensitive matches.
     2. pageDescription
     3. pageDate
     4. pageSize
  -->
  <xsl:param name="DATA_ITEM"/>
  <!-- URL of the page we are interested in. Will be just a fragment if $DATA_ITEM='urlFragment'. -->
  <xsl:param name="URL"/>
  
  <xsl:template match="/sitemap:urlset">

    <xsl:variable name="fullUrl" select="concat($BASE,$URL)"/>
    <xsl:variable name="fullUrlNode" select="sitemap:url[sitemap:loc=$fullUrl]"/>

    <xsl:choose>
      <xsl:when test="$DATA_ITEM='urlFragment'">
        <xsl:variable name="urlFragment" select="translate($URL,
          'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
          'abcdefghijklmnopqrstuvwxyz')"/>
        <xsl:for-each select="sitemap:url/sitemap:loc">
          <!-- Grab just the last segment of url -->
          <xsl:variable name="urlSegment" select="substring-after(., concat($BASE, '/pics/'))"/>
          <xsl:variable name="urlSegmentLowerCase" select="translate(
            $urlSegment,
            'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
            'abcdefghijklmnopqrstuvwxyz')"/>
          <xsl:if test="contains($urlSegmentLowerCase, $urlFragment)">
            <xsl:value-of select="substring-after(., $BASE)"/><xsl:text>&#xA;</xsl:text>
          </xsl:if>
        </xsl:for-each>
      </xsl:when>
      <xsl:when test="$DATA_ITEM='pageDescription'"><xsl:value-of select="normalize-space($fullUrlNode/jcd:desc)"/></xsl:when>
      <xsl:when test="$DATA_ITEM='pageDate'">
        <xsl:variable name="pageDate" select="$fullUrlNode/sitemap:lastmod"/>
        <xsl:if test="$pageDate != ''">
          <div>Page last modified on: <xsl:value-of select="$pageDate"/></div>
        </xsl:if>
      </xsl:when>
      <xsl:when test="$DATA_ITEM='pageSize'">
        <xsl:variable name="pageSize" select="$fullUrlNode/@jcd:dsize"/>
        <xsl:if test="$pageSize != ''">
          <div>Folder Size: <xsl:value-of select="$pageSize"/></div>
        </xsl:if>
      </xsl:when>
      <xsl:otherwise>
        <xsl:call-template name="error">
          <xsl:with-param name="urlFragment" select="$urlFragment"/>
        </xsl:call-template>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>
  
  <xsl:template name="parseItemName">
    <xsl:param name="itemName"/>
    <xsl:choose>
      <xsl:when test="contains($itemName,'/')">
        <xsl:call-template name="parseItemName">
          <xsl:with-param name="itemName" select="substring-after($itemName,'/')"/>
        </xsl:call-template>
      </xsl:when>
      <xsl:otherwise>
        <xsl:value-of select="$itemName"/>
      </xsl:otherwise>
    </xsl:choose>    
  </xsl:template>  
  
  <xsl:template name="error">
    XSLT ERROR: DATA_ITEM="<xsl:value-of select="$DATA_ITEM"/>", URL="<xsl:value-of select="$URL"/>", urlFragment="<xsl:value-of select="$urlFragment"/>"
    <xsl:choose>
      <xsl:when test="$fullUrlNode">
        [ fullUrlNode was found. ]
      </xsl:when>
      <xsl:otherwise>
        [ fullUrlNode was NOT found. ]        
      </xsl:otherwise>
    </xsl:choose>    
  </xsl:template>    

</xsl:stylesheet>
