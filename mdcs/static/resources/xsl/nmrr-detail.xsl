<?xml version="1.0" encoding="UTF-8"?>
<!--
################################################################################
#
# File Name: xml2html.xsl
# Purpose: 	Renders an XML document in HTML  
#
# Author: Guillaume SOUSA AMARAL
#         guillaume.sousa@nist.gov
#
# Sponsor: National Institute of Standards and Technology (NIST)
#
################################################################################ 
 -->
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">
	<xsl:output method="html" indent="yes" encoding="UTF-8" />	
	
	<xsl:template match="/">		
		<div style="background-color:#fafafa">
			<table>
				<tr style="background-color:#f0f0f0">
					<td style="width:180px" colspan="2">
						<xsl:variable name="url" select="//Resource/content/referenceURL" />
						<xsl:choose>
							<xsl:when test="//Resource/content/referenceURL!=''">
								<a target="_blank" href="{$url}"><xsl:value-of select="//Resource/identity/title"/></a>	
							</xsl:when>
							<xsl:otherwise>
								<xsl:value-of select="//Resource/identity/title"/>
							</xsl:otherwise>
						</xsl:choose>
					</td>
				</tr>
				<xsl:apply-templates select="/*" />
				<xsl:apply-templates select="//*[not(*)]" />
			</table>
		</div>
	</xsl:template>
	
	<xsl:template match="/*">
		<xsl:apply-templates select="@*"/>
	</xsl:template>
	
	<xsl:template match="//*[not(*)]">
		
		<xsl:variable name="name" select="name(.)" />
		<xsl:variable name="value" select="." />		
		
		<tr class="nmrr_line line_{$name}">
			<td width="180">
				<xsl:value-of select="$name" />
			</td>
			<td>
				<span class='value'>
					<xsl:choose>
						<xsl:when test="contains($name, 'URL')">
							<a target="_blank" href="{$value}"><xsl:value-of select="$value"/></a>							
						</xsl:when>
						<xsl:otherwise>
							<xsl:value-of select="$value"/>
						</xsl:otherwise>
					</xsl:choose>
				</span>
			</td>
		</tr>
		<xsl:apply-templates select="@*" />
	</xsl:template>
	
	<xsl:template match="@*">
		<xsl:variable name="name" select="name(.)" />
		<xsl:variable name="value" select="." />		
		
		<tr class="nmrr_line line_{$name}">
			<td width="180">
				<xsl:value-of select="$name" />
			</td>
			<td>
				<span class='value'>
					<xsl:choose>
						<xsl:when test="contains($name, 'URL')">
							<a target="_blank" href="{$value}"><xsl:value-of select="$value"/></a>							
						</xsl:when>
						<xsl:otherwise>
							<xsl:value-of select="$value"/>
						</xsl:otherwise>
					</xsl:choose>
				</span>
			</td>
		</tr>
	</xsl:template>
</xsl:stylesheet>