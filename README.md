








# PROJECT-2-SOC

MIT license

**PROJECT-2-SOC**
Security Operations Center system built in Python for structured security telemetry, alert triage, incident investigation, operational visibility, and integration with PROJECT FOREX.

**Status:** SOC V1 Release
**FOREX contract:** 1.x
**Platform:** Cross-platform Python environment
**Language:** Python

---

## Overview

PROJECT-2-SOC is a custom Security Operations Center (SOC) system developed as a cybersecurity engineering project.

The system provides a local security-operations layer for receiving, normalizing, storing, correlating, and presenting security events and operational state.

The project was designed around several engineering priorities:

* Structured security telemetry
* Explainable alert and incident handling
* Clear separation between ingestion, normalization, storage, detection, correlation, and presentation
* Persistent operational state
* Read-only operational interfaces where appropriate
* Bounded output and resource usage
* Runtime resilience
* Reproducible validation
* Stable integration boundaries for PROJECT FOREX

PROJECT-2-SOC operates locally and does not require a cloud service or external web server for its core functionality.

---

## Architecture

```text
                    Security Events
                           │
                           ▼
                    Event Ingestion
                           │
                           ▼
                   Event Normalization
                           │
                           ▼
                     Event Storage
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
        Event Correlation          Detection Logic
              │                         │
              └────────────┬────────────┘
                           ▼
                    Alert / Incident
                       Operations
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
            CLI        Terminal UI   FOREX View
              │            │            │
              └────────────┼────────────┘
                           ▼
                  PROJECT FOREX Boundary
```

The architecture separates event handling, security analysis, operational presentation, runtime state, and external integration so that individual components can evolve without tightly coupling the entire system.

---

## Security Operations Capabilities

PROJECT-2-SOC provides operational capabilities for working with structured security information, including:

* Event ingestion
* Event normalization
* Local event storage
* Security event correlation
* Alert triage
* Host investigation
* Incident lifecycle visibility
* Incident and advisory response views
* Runtime health visibility
* Security posture views
* FOREX operational views
* Bounded terminal output

The SOC is designed to present related security information as an operational context rather than treating every event as an isolated record.

---

## Operational Interface

PROJECT-2-SOC provides a stable Python interface together with a command-line interface and a Rich-based terminal UI.

The normal CLI and Python API do not require the interactive UI to be running.

### CLI

Display available commands:

```bash
python3 -m soc.cli --help
```

Run the SOC interface once:

```bash
python3 -m soc.cli ui --once
```

Display the alert view:

```bash
python3 -m soc.cli ui --view alerts --once
```

Omit `--once` for periodic refresh.

Plain terminal output can be requested with:

```bash
NO_COLOR=1 python3 -m soc.cli ui --once
```

Host-specific views can use:

```bash
python3 -m soc.cli ui --host FOREX-01
```

Output can be bounded with:

```bash
python3 -m soc.cli ui --max-rows 20
```

---

## Python API

PROJECT-2-SOC exposes a stable Python facade for programmatic access.

Example:

```python
from soc import FOREXWorkflow, SOCConfig, SOCService

service = SOCService(SOCConfig.from_env())
posture = FOREXWorkflow(service).security_posture("FOREX-01")
```

The public interface is intended to provide a controlled boundary between SOC internals and consumers such as PROJECT FOREX.

---

## Response Safety Model

SOC response recommendations are **advisory-only**.

Displaying a recommendation through the SOC interface does not execute a response action or automatically perform an incident lifecycle transition.

This separation keeps operational visibility distinct from potentially mutating security actions.

---

## PROJECT FOREX Integration

PROJECT-2-SOC is designed to remain an independently maintainable cybersecurity component while exposing structured operational information for PROJECT FOREX.

The SOC provides a dedicated FOREX workflow and security-operations view.

Current FOREX-facing functionality includes:

* Security posture information
* Host investigation
* Alert triage
* Incident lifecycle visibility
* Advisory response information
* Operational SOC state

The SOC integration boundary is designed to allow PROJECT FOREX to consume security information without requiring the FOREX system to depend directly on internal SOC implementation details.

---

## PROJECT FOREX Phase 2

PROJECT FOREX Phase 2 integrates three independently developed cybersecurity projects:

```text
PROJECT-1-EDR   → Endpoint Detection & Response
PROJECT-2-SOC   → Security Operations
PROJECT-3-SCAN  → Network Discovery & Scanning
                         │
                         ▼
                   PROJECT FOREX
```

Each project is developed independently and maintains its own internal architecture and operational responsibilities.

FOREX integration is performed through defined boundaries rather than tightly coupling the three systems.

---

## Installation

PROJECT-2-SOC supports Python 3.11 through 3.14.

Install the project in editable mode:

```bash
python3 -m pip install -e .
```

For development, a virtual environment is recommended:

```bash
python3 -m venv .venv
```

Activate the environment and install:

```bash
python3 -m pip install -e .
```

Runtime dependencies are defined by the project configuration.

---

## Runtime Data

SOC runtime data and generated operational artifacts should remain separated from source-controlled application code where applicable.

Runtime logs and generated state are excluded from version control according to the project's `.gitignore` configuration.

This keeps the repository focused on reproducible source code, configuration, tests, and documentation rather than machine-specific runtime artifacts.

---

## Validation

PROJECT-2-SOC includes automated validation covering its core operational components.

Validation is intended to verify:

* Event ingestion
* Event normalization
* Event storage
* Security workflows
* Operational interfaces
* FOREX integration boundaries
* Runtime behavior
* Release readiness

The repository contains the relevant test and validation infrastructure used during development and release preparation.

---

## Documentation

Additional engineering and security documentation is available in the repository.

Relevant documentation includes:

* Architecture and implementation documentation
* FOREX integration documentation
* Security operations documentation
* Release and validation documentation
* Module and interface documentation

See the `docs/` directory for the current documentation set.

---

## Current Status

**PROJECT-2-SOC V1 is released.**

The project has completed its planned development cycle and reached its final V1 release state.

The repository contains the complete development history leading to the current release.

The current SOC implementation includes:

* Core event-processing infrastructure
* Structured operational workflows
* Terminal-based operational interface
* Alert triage
* Host investigation
* Incident lifecycle views
* FOREX security operations views
* Runtime-log exclusion from source control
* Stable integration boundaries

---

## Roadmap

Future development may include:

* Additional security-event sources
* Expanded detection and correlation capabilities
* Additional operational views
* Extended incident workflows
* Additional FOREX integration capabilities
* Further runtime and performance refinement

Future work will preserve the separation between SOC operations and the independently developed EDR and SCAN projects.

---

## Project Structure

The repository is organized around distinct operational responsibilities:

```text
PROJECT-2-SOC/
├── ingestion/
├── normalization/
├── storage/
├── correlation/
├── detection/
├── alerting/
├── tests/
├── docs/
├── main.py
├── pyproject.toml
├── README.md
└── LICENSE
```

The exact implementation structure may evolve as the project develops.

---

## Author

**Jesús Bastidas**

Mechatronics student focused on cybersecurity, systems engineering, networking, Linux, and Python.

PROJECT-2-SOC was developed as part of my practical cybersecurity engineering work and as the second component of a larger set of independently developed security projects.

---

## License

This project is licensed under the MIT License.

See [`LICENSE`](LICENSE) for details.









