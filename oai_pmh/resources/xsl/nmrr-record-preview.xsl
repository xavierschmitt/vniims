<?xml version="1.0" encoding="UTF-8"?>
<!--
################################################################################
#
# File Name: nmrr-record-preview.xsl
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
	
   <xsl:param name="tbstyle">border-bottom-width: 0px;</xsl:param>

   <xsl:variable name="cr"><xsl:text>
</xsl:text></xsl:variable>

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
        <table>
          <tr style="background-color:#f0f0f0">
           <td>
            <xsl:choose xml:space="default">
              <xsl:when test="$home!=''">
                <a target="_blank" href="{$home}"><xsl:value-of select="$title"/></a>
              </xsl:when>
              <xsl:otherwise><xsl:value-of select="$title"/></xsl:otherwise>
            </xsl:choose>
            <xsl:if test="*/resourceType">
            <br />
            <font size="-1"><em>Resource Type:  </em>  <xsl:value-of select="*/resourceType"/></font>
            </xsl:if>
           </td><td>
            <div style="margin-top:5px;font-size:20px;float:right">
              <div style="float:right;margin:-10px 0px 0px 0px">
{% if oai_pmh %}
                <button class="btn" onclick="dialog_detail_oai_pmh('{{{{id}}}}');" title="Click to view resource metadata.">Resource Metadata</button>
{% else %}	
                <button class="btn" onclick="dialog_detail('{{{{id}}}}');" title="Click to view resource metadata.">Resource Metadata</button>	
{% endif %}							
                <xsl:choose>
                  <xsl:when test="$home!=''">
                    <a target="_blank" href="{$home}"><button class="btn" title="Click to visit the resource's home page.">Go To</button></a>
                  </xsl:when>
                </xsl:choose>    
              </div>
            </div>
          </td></tr>
          <tr><td colspan="2">
            <xsl:apply-templates select="/*" mode="brief"/>
            <xsl:apply-templates select="/*" mode="full"/>
          </td></tr>
        </table>
      </div>
   </xsl:template>

   <xsl:template match="/*" mode="brief" xml:space="preserve">
      <div class="nmrrec_brief">
        <table>
         <xsl:if test="publisher">
         <tr>
          <td width="25%"><em>Publisher:</em></td>
          <td>
            <xsl:apply-templates select="publisher" mode="brief"/>
            <xsl:if test="publicationYear">
              <xsl:text> (</xsl:text>
              <xsl:value-of select="normalize-space(publicationYear)"/>
              <xsl:text>)</xsl:text>
            </xsl:if>
          </td>
         </tr>
         </xsl:if>
         <tr>
          <td width="25%"><em>Sponsoring Country:</em></td>
          <td>
            <xsl:apply-templates select="sponsoringCountry" mode="brief"/>
          </td>
         </tr>
         <tr>
          <td><em>Subject:</em></td>
          <td>
            <xsl:call-template name="comma-delimit">
               <xsl:with-param name="elname">subject</xsl:with-param>
            </xsl:call-template>
          </td>
         </tr>
         <xsl:apply-templates select="measures" mode="brief"/>
        </table>
      </div>
   </xsl:template>

   <xsl:template match="sponsoringCountry" mode="brief">
      <xsl:choose>
        <xsl:when test="abbrev"><xsl:value-of select="abbrev"/></xsl:when>
        <xsl:otherwise><xsl:value-of select="name"/></xsl:otherwise>
      </xsl:choose>
   </xsl:template>

   <xsl:template match="measures" mode="brief">
      <xsl:if test="dataStatus">
         <tr><td><em>Data status: </em></td>
             <td>
               <xsl:call-template name="comma-delimit">
                  <xsl:with-param name="elname">dataStatus</xsl:with-param>
               </xsl:call-template>
             </td></tr>
      </xsl:if>
      <xsl:if test="documentStatus">
         <tr><td><em>Document status: </em></td>
             <td>
               <xsl:call-template name="comma-delimit">
                  <xsl:with-param name="elname">documentStatus</xsl:with-param>
               </xsl:call-template>
             </td></tr>
      </xsl:if>
      <xsl:if test="propertyType">
         <tr><td><em>Property type: </em></td>
             <td>
               <xsl:call-template name="comma-delimit">
                  <xsl:with-param name="elname">propertyType</xsl:with-param>
               </xsl:call-template>
             </td></tr>
      </xsl:if>
      <xsl:if test="chemicalConstituent">
         <tr><td><em>Relevant substances: </em></td>
             <td>
               <xsl:call-template name="comma-delimit">
                  <xsl:with-param name="elname">chemicalConstituent</xsl:with-param>
               </xsl:call-template>
             </td></tr>
      </xsl:if>
   </xsl:template>

   <xsl:template match="measures">
      <tr><td style="{$tbstyle}">

      <dl>
        <dt> Metrology Information: </dt>
        <xsl:call-template name="multivaluedd">
           <xsl:with-param name="elname">dataStatus</xsl:with-param>
           <xsl:with-param name="label">Data status</xsl:with-param>
        </xsl:call-template>
        <xsl:call-template name="multivaluedd">
           <xsl:with-param name="elname">propertyType</xsl:with-param>
           <xsl:with-param name="label">Property types</xsl:with-param>
        </xsl:call-template>
        <xsl:call-template name="multivaluedd">
           <xsl:with-param name="elname">propertyName</xsl:with-param>
           <xsl:with-param name="label">Property names</xsl:with-param>
        </xsl:call-template>
        <xsl:call-template name="multivaluedd">
           <xsl:with-param name="elname">dataCollectionMethod</xsl:with-param>
           <xsl:with-param name="label">Data collection method types</xsl:with-param>
        </xsl:call-template>
        <xsl:call-template name="multivaluedd">
           <xsl:with-param name="elname">materialType</xsl:with-param>
           <xsl:with-param name="label">Material type</xsl:with-param>
        </xsl:call-template>
        <xsl:for-each select="materialName">
          <xsl:call-template name="multivaluedd">
             <xsl:with-param name="elname">technical</xsl:with-param>
             <xsl:with-param name="label">Material names (technical)</xsl:with-param>
          </xsl:call-template>
          <xsl:call-template name="multivaluedd">
             <xsl:with-param name="elname">trade</xsl:with-param>
             <xsl:with-param name="label">Material names (trade)</xsl:with-param>
          </xsl:call-template>
        </xsl:for-each>
        <xsl:call-template name="multivaluedd">
           <xsl:with-param name="elname">supplier</xsl:with-param>
           <xsl:with-param name="label">Material Suppliers</xsl:with-param>
        </xsl:call-template>
        <xsl:call-template name="multivaluedd">
           <xsl:with-param name="elname">chemicalConstituent</xsl:with-param>
           <xsl:with-param name="label">Relevant substances</xsl:with-param>
        </xsl:call-template>
        <dd><em>Quality metrics:</em>
            <ul>
              <xsl:apply-templates select="qualityMetric" />
            </ul>
        </dd>
      </dl>
      </td></tr>
   </xsl:template>

   <xsl:template match="qualityMetric">
      <xsl:for-each select="*[.='Yes']">
        <xsl:value-of select="$cr"/>
        <li> 
          <xsl:choose>
            <xsl:when test="local-name()='calibratedEquipment'">Calibrated equipment traceable to primary standards</xsl:when>
            <xsl:when test="local-name()='standardMethods'">Use of recognized standard measurement method </xsl:when>
            <xsl:when test="local-name()='characterizedUncertainties'">Characterized uncertainties</xsl:when>
            <xsl:when test="local-name()='multisiteMeasurements'">Reported valued based on multi-site measurements</xsl:when>
            <xsl:when test="local-name()='sampleStability'">Stability or maturity of measured samples described</xsl:when>
            <xsl:when test="local-name()='referenceMaterials'">Measurements made on certified reference materials</xsl:when>
            <xsl:when test="local-name()='reviewAndCertification'">Documentation of review and/or certification</xsl:when>
            <xsl:when test="local-name()='criticalLiteratureReview'">Data compiled through critical review of values from peer-reviewed literature</xsl:when>
            <xsl:otherwise>matching problem: <xsl:value-of select="local-name()"/></xsl:otherwise>
          </xsl:choose>
        </li>
      </xsl:for-each>
    </xsl:template>

    <xsl:template name="multivaluedd">
       <xsl:param name="elname"/>
       <xsl:param name="label" select="$elname"/>
       <xsl:if test="*[local-name()=$elname]">
         <dd>
          <em><xsl:value-of select="$label"/><xsl:text>: </xsl:text></em>
              <xsl:call-template name="comma-delimit">
                <xsl:with-param name="elname" select="$elname"/>
              </xsl:call-template>
         </dd>
       </xsl:if>
    </xsl:template>

    <xsl:template match="*" mode="measures">

    </xsl:template>



    <xsl:template match="access">
      <tr><td style="{$tbstyle}">
      <dl>
        <dt>Access Information:</dt>
        <dd><xsl:apply-templates select="rights" /></dd>
        <dd>
        <xsl:apply-templates select="licenseName" />
        <xsl:apply-templates select="termsURL" /></dd>
        <xsl:choose>
          <xsl:when test="via">
           <xsl:apply-templates select="via" />
          </xsl:when>
          <xsl:otherwise>
           <dd><xsl:text>To access this resource, </xsl:text>
           <a href="{$home}">visit its home page</a></dd>
          </xsl:otherwise>
        </xsl:choose>
      </dl>
      </td></tr>
    </xsl:template>

    <xsl:template match="rights">
       <xsl:choose>
          <xsl:when test=".='public'">
            <em>
            <xsl:text>This resource is publically available; no login required.</xsl:text>
            </em>
          </xsl:when>
          <xsl:when test=".='open-login'">
            <em>
            <xsl:text>This resource is openly available; though, login is required.</xsl:text>
            </em>
          </xsl:when>
          <xsl:when test=".='proprietary'">
            <em>
            <xsl:text>This resource is available only to authorized users.</xsl:text>
            </em>
          </xsl:when>
          <xsl:when test=".='fee-required'">
            <em>
            <xsl:text>A fee is required to access this resource.</xsl:text>
            </em>
          </xsl:when>
       </xsl:choose>
    </xsl:template>

    <xsl:template match="licenseName">
       <em>License: </em>
       <xsl:value-of select="."/>
    </xsl:template>
    <xsl:template match="termsURL">
       <xsl:text>(See </xsl:text>
       <a href="{normalize-space(.)}">terms of use</a>
       <xsl:text>)</xsl:text>
    </xsl:template>

    <xsl:template match="via[contains(@xsi:type,':Download')]">
       <dl>
         <dt><em>Available for Download</em></dt>
         <xsl:apply-templates select="description" />
         <xsl:apply-templates select="." mode="formats"/>
         <xsl:apply-templates select="accessURL"/>
       </dl>
    </xsl:template>

    <xsl:template match="via/description">
       <dd><xsl:value-of select="."/></dd>
    </xsl:template>
    <xsl:template match="via[format]" mode="formats">
       <dd><em>Available Formats: </em>
       <xsl:call-template name="comma-delimit">
          <xsl:with-param name="elname">format</xsl:with-param>
       </xsl:call-template></dd>
    </xsl:template>
    <xsl:template match="via" mode="formats"/>
    <xsl:template match="via/accessURL">
       <dd>Download URL: <a href="{.}"><xsl:value-of select="."/></a></dd>
    </xsl:template>

    <xsl:template match="via[contains(@xsi:type,':ServiceAPI')]">
       <dl>
         <dt><em>Accessible via Service API</em></dt>
         <xsl:apply-templates select="description" />
         <xsl:apply-templates select="documentationURL" />
       </dl>
    </xsl:template>

    <xsl:template match="via/documentationURL">
       <dd><em>Service documentation URL</em>
           <a href="{.}"><xsl:value-of select="."/></a></dd>
    </xsl:template>

    <xsl:template match="via[contains(@xsi:type,':Media')]">
      <dl>
        <dt><em>This data is available via the following storage media: </em>
        <xsl:call-template name="comma-delimit">
           <xsl:with-param name="elname">mediaType</xsl:with-param>
        </xsl:call-template></dt>
        <xsl:apply-templates select="description" />
        <xsl:apply-templates select="requestURL" />
      </dl>      
    </xsl:template>

    <xsl:template match="via/requestURL">
       <dd><em>
       <xsl:text>Request media on-line: </xsl:text>
       </em><a href="{normalize-space(.)}"><xsl:value-of select="."/></a></dd>
    </xsl:template>

    <xsl:template name="comma-delimit">
       <xsl:param name="elname"/>
       <xsl:for-each select="*[local-name()=$elname]">
          <xsl:if test="position()>1"><xsl:text>, </xsl:text></xsl:if>
          <xsl:value-of select="."/>
       </xsl:for-each>
    </xsl:template>

    <xsl:template match="/*" mode="full">
       <div class="nmrrec_full">
         <table>
          <tr>
           <td style="{$tbstyle}">
             <xsl:apply-templates select="subtitle" />
             <xsl:apply-templates select="." mode="abbreviations"/><br />
             <xsl:choose>
               <xsl:when test="publisher">
                 <xsl:apply-templates select="publisher" />
                 <xsl:text> (</xsl:text>
                 <xsl:apply-templates select="sponsoringCountry" mode="brief"/>
                 <xsl:text>)</xsl:text>
               </xsl:when>
               <xsl:otherwise>
                 <em>Sponsoring Country: </em>
                 <xsl:value-of select="sponsoringCountry/name"/>
                 <xsl:if test="sponsoringCountry/abbrev">
                    <xsl:text> (</xsl:text>
                    <xsl:value-of select="sponsoringCountry/abbrev"/>
                    <xsl:text>)</xsl:text>
                 </xsl:if>
               </xsl:otherwise>
             </xsl:choose><br />
             <xsl:apply-templates select="publicationYear" />
             <xsl:apply-templates select="." mode="homepage"/>
           </td>
          </tr>
          <tr>
           <td style="{$tbstyle}">
             <xsl:apply-templates select="contact" />
           </td>
          </tr>
          <xsl:if test="creator or contributor">
          <tr>
           <td style="{$tbstyle}">
             <xsl:apply-templates select="self::node()[creator or contributor]"
                                  mode="contributors"/>
           </td>
          </tr>
          </xsl:if>
          <tr>
           <td style="{$tbstyle}">
             <xsl:apply-templates select="." mode="descriptions"/>
             <xsl:if test="subject">
               <em>Subjects: </em>
               <xsl:call-template name="comma-delimit">
                  <xsl:with-param name="elname">subject</xsl:with-param>
               </xsl:call-template><br/>
             </xsl:if>
             <xsl:if test="applicationArea">
               <xsl:value-of select="$cr"/>
               <em>Application Areas: </em>
               <xsl:call-template name="comma-delimit">
                  <xsl:with-param name="elname">applicationArea</xsl:with-param>
               </xsl:call-template><br/>
             </xsl:if>
           </td>
          </tr>
          <xsl:apply-templates select="measures" />
          <xsl:apply-templates select="access" />
         </table>
       </div>
    </xsl:template>

    <xsl:template match="subtitle">
       <em>Subtitle: </em>
       <xsl:value-of select="."/><br />
    </xsl:template>

    <xsl:template match="publisher">
       <em>Publisher: </em>
      <xsl:value-of select="."/>
   </xsl:template>

   <xsl:template match="publicationYear">
      <em>Publication Year: </em>
      <xsl:value-of select="."/><br />
   </xsl:template>

   <xsl:template match="*[abbreviation]" mode="abbreviations">
      <em>
      <xsl:text>Abbreviation</xsl:text>
      <xsl:if test="count(abbreviation) > 1">
        <xsl:text>s</xsl:text>
      </xsl:if>
      <xsl:text>: </xsl:text>
      </em>
      <xsl:call-template name="comma-delimit">
         <xsl:with-param name="elname">abbreviation</xsl:with-param>
      </xsl:call-template>
   </xsl:template>
   <xsl:template match="*" mode="abbreviations"/>

   <xsl:template match="*[homePage or homeURL]" mode="homepage">
     <xsl:choose>
       <xsl:when test="homePage/doi">
         <a href="{$home}">
           <xsl:text>doi:</xsl:text>
           <xsl:value-of select="homePage/doi"/>
         </a>
       </xsl:when>
       <xsl:otherwise>
         <em>Home page: </em>
         <a href="{$home}"><xsl:value-of select="$home"/></a>
       </xsl:otherwise>
     </xsl:choose>
   </xsl:template>
   <xsl:template match="*" mode="homepage"/>

   <xsl:template match="contact">
     <dl>
       <dt>Contact Information</dt>
       <xsl:for-each select="*">
          <dd><em>
              <xsl:value-of select="local-name()"/><xsl:text>: </xsl:text></em>
              <xsl:value-of select="."/> </dd>
       </xsl:for-each>
     </dl>
   </xsl:template>

   <xsl:template match="*[creator or contributor]" mode="contributors">
     <dl>
       <dt>Authors and Contributors</dt>
       <xsl:for-each select="creator">
          <dd><em>Creator: </em>
              <xsl:value-of select="name"/>
              <xsl:if test="affiliation">
              <xsl:text> (</xsl:text>
              <xsl:value-of select="affiliation"/>
              <xsl:text>)</xsl:text>
              </xsl:if>
              </dd>
       </xsl:for-each>
       <xsl:for-each select="contributor">
          <dd><em>
              <xsl:value-of select="@type"/>
              <xsl:text>: </xsl:text></em>
              <xsl:value-of select="name"/>
              <xsl:if test="affiliation">
              <xsl:text> (</xsl:text>
              <xsl:value-of select="affiliation"/>
              <xsl:text>)</xsl:text>
              </xsl:if>
              </dd>
       </xsl:for-each>
     </dl>
   </xsl:template>
   <xsl:template match="*" mode="contributors"/>

   <xsl:template match="*[description]" mode="descriptions">
      <dl>
        <dt><em>Description: </em></dt>
        <dd>
           <xsl:for-each select="description">
              <xsl:if test="position()!=1">
              <xsl:text>
   </xsl:text><br/><br/>
              <xsl:text>
   </xsl:text>
              </xsl:if>
              <xsl:value-of select="."/>
           </xsl:for-each>
        </dd>
      </dl>
   </xsl:template>
   <xsl:template match="*" mode="descriptions"/>

</xsl:stylesheet>
