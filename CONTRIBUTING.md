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
5. Install all dependencies: `pip install -r requirements.lock`

> **Nota:** Usiamo `requirements.lock` per installare le dipendenze. Questo file garantisce che tutti i collaboratori e le pipeline di CI/CD usino le stesse esatte versioni di ogni pacchetto, assicurando un ambiente di sviluppo riproducibile.

## Development Guidelines

### Flusso di Sviluppo

Per contribuire al progetto, segui questi passaggi:

1. **Crea un nuovo branch**: Parti dal branch `develop` e crea un branch per la tua modifica.
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/nome-della-tua-feature
   ```
2. **Apporta le tue modifiche**: Scrivi il codice e la documentazione necessaria.
3. **Esegui i test**: Assicurati che tutti i test passino.
   ```bash
   python -m pytest
   ```
4. **Controlla lo stile del codice**: Verifica che il tuo codice sia conforme alle linee guida di stile.
   ```bash
   flake8 .
   ```
5. **Fai il commit delle tue modifiche**: Usa messaggi di commit chiari e descrittivi.
   ```bash
   git commit -m "feat: Aggiunge la nuova funzionalità X"
   ```
6. **Apri una Pull Request**: Fai il push del tuo branch sul tuo fork e apri una Pull Request verso il branch `develop` del repository principale.

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
2. Update the `README.md` and other relevant documentation with details of changes to the interface.
3. You may merge the Pull Request in once you have the sign-off of at least one other developer, or if you do not have permission to do that, you may request the reviewer to merge it for you. The project maintainers will handle version bumping.
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
- Run the linter to check your code:
  ```bash
  flake8 .
  ```

### Commit Message Style

- We recommend using Conventional Commits for commit messages. This helps maintain a clear and readable history.
  - `feat:` for new features.
  - `fix:` for bug fixes.
  - `docs:` for documentation changes.
  - `style:` for code style changes.
  - `refactor:` for code refactoring.
  - `test:` for adding or improving tests.

### Documentation Style Guide

- Use Italian for all user-facing documentation
- Use English for code comments and technical documentation
- Follow accessibility guidelines for documentation
- Include examples where helpful

## Questions?

If you have questions about contributing, feel free to open an issue or contact the maintainers. We're here to help make your contribution successful while maintaining the highest standards of security, privacy, and compliance with Italian public administration requirements.

Remember that this project serves the public interest and all contributions should align with the mission of enhancing transparency and efficiency in Italian public administration.