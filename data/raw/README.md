# Fintech Document Intelligence - Data Sources

## Overview

This directory contains real, publicly available financial documents downloaded from official sources.

## Data Sources Summary


### EUR-Lex (4 documents)

| Filename | Type | Description | Size (MB) |
|----------|------|-------------|----------|
| mifid2_directive_2014.html | regulation | Markets in Financial Instruments Directive | 0.00 |
| psd2_directive_2015.html | regulation | Payment Services Directive | 0.00 |
| gdpr_regulation_2016.html | regulation | General Data Protection Regulation | 0.00 |
| crr_regulation_2013.html | regulation | Capital Requirements Regulation | 0.00 |

### BIS Basel Committee (2 documents)

| Filename | Type | Description | Size (MB) |
|----------|------|-------------|----------|
| basel3_finalising_reforms.pdf | regulation | Basel III: Finalising post-crisis reforms | 2.91 |
| basel_operational_risk.pdf | regulation | Principles for operational resilience | 1.28 |


## Document Types

- **annual_report**: Annual financial reports (10-K filings)
- **regulation**: EU and Basel regulations
- **guidance**: Supervisory guidance from regulators
- **contract**: Standard financial contract templates

## Usage

These documents are used for:
1. Training and evaluating the document intelligence system
2. Testing retrieval accuracy
3. Validating compliance checking capabilities
4. Demonstrating real-world applicability

## Legal & Compliance

All documents are:
- Publicly available from official sources
- Free to use for research and development
- Properly attributed to their sources
- Covered under fair use for AI research

## Sources

- **SEC Edgar**: U.S. Securities and Exchange Commission
- **EUR-Lex**: EU Legal Database
- **BaFin**: German Federal Financial Supervisory Authority
- **BIS Basel Committee**: Bank for International Settlements
- **ECB**: European Central Bank

## Last Updated

Dataset compiled: 2026-02-04

## Notes

Some documents are in HTML format (SEC filings, EU regulations) and require HTML parsing.
Others are PDF format and require PDF extraction.

All documents have been verified for:
- Accessibility
- Authenticity
- Relevance to fintech use cases
