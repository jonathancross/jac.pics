<?xml version="1.0" encoding="UTF-8"?>
<!-- 
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
  <xsl:param name="NAME"/>
  <xsl:param name="VALUE"/>
  <xsl:variable name="base">http://pics.jonathancross.com</xsl:variable>
  <xsl:variable name="ID" select="concat($base,$VALUE)"/>
  <xsl:variable name="NODE" select="/sitemap:urlset/sitemap:url[sitemap:loc=$ID]"/>
  
  <xsl:template match="/sitemap:urlset">
    <xsl:choose>
      <xsl:when test="$NAME='pageDescription'"><xsl:value-of select="normalize-space($NODE/jcd:desc)"/></xsl:when>
      <xsl:when test="$NAME='pageDate'">
        <xsl:variable name="pageDate" select="$NODE/sitemap:lastmod"/>
        <xsl:if test="$pageDate != ''">
            <div>Last Modified: <xsl:value-of select="$pageDate"/></div>
        </xsl:if>
      </xsl:when>
      <xsl:when test="$NAME='pageSize'">
        <xsl:variable name="pageSize" select="$NODE/@jcd:dsize"/>
        <xsl:if test="$pageSize != ''">
          <div>Folder Size: <xsl:value-of select="$pageSize"/></div>
        </xsl:if>
      </xsl:when>
      <xsl:otherwise>
        <xsl:call-template name="error"/>
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
    XSLT ERROR: NAME="<xsl:value-of select="$NAME"/>", VALUE="<xsl:value-of select="$VALUE"/>", ID="<xsl:value-of select="$ID"/>"
    <xsl:choose>
      <xsl:when test="$NODE">
        [ NODE was found. ]
      </xsl:when>
      <xsl:otherwise>
        [ NODE was NOT found. ]        
      </xsl:otherwise>
    </xsl:choose>    
  </xsl:template>    

</xsl:stylesheet>
