# Security Policy

## Supported Version

Security fixes are applied to the latest revision of the `main` branch.

## Reporting a Vulnerability

Please use the repository's **Security** tab and select **Report a vulnerability** to submit a private vulnerability report through GitHub Private Vulnerability Reporting.

Do not disclose an unpatched vulnerability in a public issue or discussion. Do not include production credentials, personal data, customer documents, or other sensitive information in a report. If a minimal reproduction needs sensitive-looking values, replace them with synthetic placeholders.

The maintainer will acknowledge the report when possible, investigate its impact, and coordinate disclosure after a fix is available.

## Deployment Scope

The Docker Compose configuration is intended for local development. Internet-facing deployments must replace all example credentials, restrict infrastructure ports, protect secrets outside the repository, and use TLS and appropriate network access controls.
