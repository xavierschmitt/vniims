<?xml version="1.0" encoding="UTF-8"?>
<!--
################################################################################
#
# File Name: nmrr-record-page.xsl
# Purpose: 	Renders an XML document in HTML  
#
# Author: Ray Plante
#         raymond.plante@nist.gov
#
# Sponsor: National Institute of Standards and Technology (NIST)
#
################################################################################ 
 -->
<xsl:stylesheet xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0"
	        xmlns:nr="urn:nist.gov/nmrr.res/1.0wd">
   <xsl:output method="html" encoding="UTF-8" />


   <xsl:param name="indent">10px</xsl:param>
   <xsl:param name="tbstyle">border-bottom-width: 0px; padding: 0px; padding-right: 10px; padding-bottom: 5px;</xsl:param>
	
   <xsl:variable name="home">
      <xsl:choose>
         <xsl:when test="/*/homePage/doi">
            <xsl:text>http://dx.doi.org/</xsl:text>
            <xsl:value-of select="normalize-space(/*/homePage/doi)"/>
         </xsl:when>
         <xsl:otherwise>
            <xsl:value-of
                 select="normalize-space(//nr:Resource/nr:content/nr:referenceURL|
                                         */homeURL|/*/homePage/url)" />
         </xsl:otherwise>
      </xsl:choose>
   </xsl:variable>
   <xsl:variable name="title">
      <xsl:value-of select="normalize-space(/*/title|/*/nr:identity/nr:title)"/>
   </xsl:variable>

   <xsl:template match="/" xml:space="preserve">
      <div style="background-color:#fafafa">
        <table cellspacing="0" cellpadding="0">
          <tr style="background-color:#f0f0f0">
           <td valign="top" style="margin-left: {$indent}">
            <xsl:choose xml:space="default">
              <xsl:when test="$home!=''">
                <a target="_blank" href="{$home}"><xsl:value-of select="$title"/></a>
              </xsl:when>
              <xsl:otherwise><xsl:value-of select="$title"/></xsl:otherwise>
            </xsl:choose>
           </td></tr>
           <tr><td style="margin-left: {$indent}">
              <xsl:apply-templates select="/*"/>
           </td></tr>
        </table>
      </div>
   </xsl:template>

   <xsl:template match="*[local-name()='Resource']" priority="1">
      <strong>Resource Metadata</strong>
      
      <table border="0" cellspacing="0" cellpadding="0" width="100%"
             style="margin-left: {$indent}">
        <tr><td colspan="2" style="margin-left: {$indent}; {$tbstyle}">
          <table border="0" cellspacing="0" cellpadding="0" width="100%"
                 style="margin-left: {$indent}">
             <xsl:apply-templates select="@localid" />
             <xsl:apply-templates select="@status" />
          </table>
        </td></tr>
        <xsl:apply-templates select="*" />        
      </table>
   </xsl:template>

   <xsl:template match="*[*]" priority="0">
      <tr><td style="{$tbstyle} padding-bottom: 0px;" colspan="2">
        <strong><em><xsl:value-of select="local-name()"/>: </em></strong>
      </td></tr>
      <tr><td style="{$tbstyle}" colspan="2">
        <table border="0" cellspacing="0" cellpadding="0" width="100%"
               style="margin-left: {$indent};">
           <xsl:apply-templates select="@*">
              <xsl:with-param name="bold" select="false()"/>
           </xsl:apply-templates>
           <xsl:apply-templates select="*" />
        </table>
      </td></tr>
   </xsl:template>

   <xsl:template match="*[not(*)]">
     <xsl:apply-templates select="." mode="fmt_md"/>
   </xsl:template>

   <xsl:template match="@*">
     <xsl:apply-templates select="." mode="fmt_md">
       <xsl:with-param name="bold" select="false()"/>
     </xsl:apply-templates>
   </xsl:template>

   <xsl:template match="*|@*" mode="fmt_md" xml:space="preserve">
      <xsl:param name="bold" select="true()"/>
      <xsl:param name="label" select="local-name()"/>
      <xsl:param name="value"><xsl:value-of select="."/></xsl:param>

      <tr>
        <td width="20em" nowrap="true" style="{$tbstyle}">
        <xsl:choose>
          <xsl:when test="$bold">
            <strong><em><xsl:value-of select="$label"/>:</em></strong>
          </xsl:when>
          <xsl:otherwise>
            <em><xsl:value-of select="$label"/>:</em>
          </xsl:otherwise>
        </xsl:choose>
        </td>
        <td style="{$tbstyle}"><xsl:copy-of select="$value"/></td>
      </tr>
   </xsl:template>

   <xsl:template match="@xsi:type">
     <xsl:apply-templates select="." mode="fmt_md">
       <xsl:with-param name="label">template</xsl:with-param>
       <xsl:with-param name="bold" select="false()"/>
       <xsl:with-param name="value" select="substring-after(.,':')"/>
     </xsl:apply-templates>
   </xsl:template>

   <xsl:template match="emailAddress" priority="1">
     <xsl:apply-templates select="." mode="fmt_md">
       <xsl:with-param name="value">
         <a href="mailto:{.}" style="color: blue;"><xsl:value-of select="."/></a>
       </xsl:with-param>
     </xsl:apply-templates>
   </xsl:template>

   <xsl:template match="subtitle" priority="1">
     <xsl:apply-templates select="." mode="fmt_md">
        <xsl:with-param name="label">altTitle: Subtitle</xsl:with-param>
     </xsl:apply-templates>
   </xsl:template>
   <xsl:template match="abbreviation" priority="1">
     <xsl:apply-templates select="." mode="fmt_md">
        <xsl:with-param name="label">altTitle: Abbreviation</xsl:with-param>
     </xsl:apply-templates>
   </xsl:template>

   <xsl:template match="termsURL" priority="1">
     <xsl:apply-templates select="." mode="fmt_md">
       <xsl:with-param name="label">termsOfUse</xsl:with-param>
       <xsl:with-param name="value">
          <a href="{.}" target="_top" style="color: blue;">
          <xsl:value-of select="."/>
          </a>
       </xsl:with-param>
     </xsl:apply-templates>
   </xsl:template>

   <xsl:template match="homePage[contains(@xsi:type,':DOI')]" priority="1">
     <xsl:apply-templates select="." mode="fmt_md">
       <xsl:with-param name="label">identifier: DOI</xsl:with-param>
       <xsl:with-param name="value">
         <xsl:value-of select="doi"/>
       </xsl:with-param>
     </xsl:apply-templates>
     <xsl:apply-templates select="." mode="fmt_md">
       <xsl:with-param name="label">homePage</xsl:with-param>
       <xsl:with-param name="value">
         <a href="{url}" target="_top" style="color: blue;"><xsl:value-of select="url"/></a>
       </xsl:with-param>
     </xsl:apply-templates>
   </xsl:template>

   <xsl:template match="homeURL" priority="1">
     <xsl:apply-templates select="." mode="fmt_md">
       <xsl:with-param name="label">homePage</xsl:with-param>
       <xsl:with-param name="value">
          <a href="{.}" target="_top" style="color: blue;">
          <xsl:value-of select="."/>
          </a>
       </xsl:with-param>
     </xsl:apply-templates>
   </xsl:template>

   <xsl:template match="*[starts-with(.,'http://') or starts-with(.,'https://')]">
     <xsl:apply-templates select="." mode="fmt_md">
       <xsl:with-param name="value">
          <a href="{.}" target="_top" style="color: blue;">
          <xsl:value-of select="."/>
          </a>
       </xsl:with-param>
     </xsl:apply-templates>
   </xsl:template>

</xsl:stylesheet>
