# Contributing to Albo Pretorio Audit Delivery

Thank you for your interest in contributing to the Albo Pretorio Audit Delivery project! This document outlines the guidelines for contributing to this project, which is designed to support transparency and efficiency in Italian public administration.

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Guidelines](#development-guidelines)
4. [Security Guidelines](#security-guidelines)
5. [Privacy Guidelines](#privacy-guidelines)
6. [Pull Request Process](#pull-request-process)
7. [Style Guides](#style-guides)
8. [Questions?](#questions)

## Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md). Please read it before contributing.

## Getting Started

### Prerequisites

- Python 3.8+
- Git
- Basic understanding of Italian public administration documents and transparency requirements

### Setup

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/albo-pretorio-audit-delivery.git`
3. Create a virtual environment: `python -m venv venv`
4. Activate the virtual environment: `source venv/bin/activate` (Linux/Mac) or `venv\Scripts\activate` (Windows)
5. Install dependencies: `pip install -r requirements.txt`

## Development Guidelines

### General Principles

1. **Public Administration Focus**: All contributions should enhance the system's ability to support Italian public administration transparency requirements.
2. **Data Minimization**: Only process the minimum amount of data necessary for the intended purpose.
3. **Privacy by Design**: Implement privacy protections from the ground up.
4. **Security First**: Security considerations must be integrated into every feature.

### Technical Requirements

- Write tests for new functionality
- Ensure all existing tests pass
- Update documentation as needed
- Follow the style guides outlined below
- Make sure your changes are compliant with Italian regulations (D.Lgs. 33/2013, GDPR, CAD)

## Security Guidelines

### Critical Security Rules

1. **Never hardcode API keys or credentials** in the source code
2. **Never use `eval()`, `exec()`, or similar dangerous functions** with user input
3. **Always validate and sanitize inputs** before processing
4. **Implement proper error handling** without exposing sensitive information
5. **Follow secure coding practices** to prevent injection attacks

### Authentication and Authorization

- If adding authentication features, ensure they comply with SPID (Sistema Pubblico di Identità Digitale) guidelines
- Implement proper session management
- Use HTTPS in all communication channels

## Privacy Guidelines

### Data Handling

1. **No personal data storage**: The system should not store personal data permanently
2. **Anonymization**: Where possible, anonymize data before processing
3. **Right to erasure**: Implement mechanisms for data deletion when required
4. **Data retention**: Follow Italian legal requirements for document retention (typically 5 years for public documents)

### Compliance Requirements

- Ensure all changes comply with GDPR
- Follow D.Lgs. 196/2003 (Italian privacy legislation)
- Respect CAD provisions on digital administration
- Align with AgID guidelines for public sector systems

## Pull Request Process

1. Ensure any install or build dependencies are removed before the end of the layer when doing a build
2. Update the README.md with details of changes to the interface, this includes new environment variables, exposed ports, useful file locations and container parameters
3. Increase the version numbers in any examples files and the README.md to the new version that this Pull Request would represent
4. You may merge the Pull Request in once you have the sign-off of two other developers, or if you do not have permission to do that, you may request the second reviewer to merge it for you
5. All contributions must pass security and privacy compliance checks

### Pull Request Template

When submitting a pull request, please include:

- Summary of changes
- Related issues (if any)
- Security implications (if any)
- Privacy considerations (if any)
- Testing performed
- Compliance verification (with Italian regulations)

## Style Guides

### Python Style Guide

- Follow PEP 8 guidelines
- Use type hints where possible
- Write docstrings for all functions and classes
- Keep functions focused and concise

### Documentation Style Guide

- Use Italian for all user-facing documentation
- Use English for code comments and technical documentation
- Follow accessibility guidelines for documentation
- Include examples where helpful

## Questions?

If you have questions about contributing, feel free to open an issue or contact the maintainers. We're here to help make your contribution successful while maintaining the highest standards of security, privacy, and compliance with Italian public administration requirements.

Remember that this project serves the public interest and all contributions should align with the mission of enhancing transparency and efficiency in Italian public administration.