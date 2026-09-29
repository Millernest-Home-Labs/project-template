# API Integration Excellence

**Purpose.** Guide GitHub Copilot to generate and modify API specifications that conform to Integration Excellence checks.  
**Scope.** Applies to all OpenAPI definitions and API-related changes in this repository.

---

## Golden Rules (Copilot MUST follow)

1) **Use OpenAPI YAML 3.0.2+** for all API specs. 
2) **Title:** 8–50 characters, clearly reflects the API’s function, and **aligns with BIAN taxonomy** where applicable. 
3) **Reusability first:** Prefer reuse of existing components, schemas, headers, parameters, and responses within this repo before creating new ones. If a capability exists, **reuse it**. 
4) **Description quality:** Provide a rich description of functionality, prerequisites/dependencies, and a brief “how it works internally” snapshot. Use rich text/links via `externalDocs` for more info. 
5) **Contacts & Terms:** Populate `info.contact` with a maintainers’ team email (or individual if team email unavailable) and include `termsOfService` if applicable. 
6) **Paths are mandatory:** Include **at least one endpoint** under `paths`, and each operation **must** reference a tag from `tags`. 
7) **Descriptions everywhere:** Every field (schemas, properties, parameters, responses, headers) requires a clear `description`. 
8) **Security:** Define **at least one** security scheme and default to **OAuth 2.0**; apply it at the global or operation level. 
9) **Versioning:** Expose an explicit **URL version segment** (e.g., `/v1`, `/v2`) per standards. 
10) **Health endpoints:** Define `/health`, with **warnings if** `/health/readiness` and `/health/liveness` are missing. Prefer including all three. 
11) **Parameters:** Use relevant, self‑explanatory names and provide descriptions for each. 
12) **Components:** Include a `components` section; favor `$ref` reuse across endpoints. 
13) **Servers:** Provide at least one valid `servers.url` with a description for the intended environment(s). 
14) **Standard headers:** Define and use **`Authorization`** and **`X-Correlation-ID`** headers (exact names). 
15) **Naming conventions & API standards:** Follow GMF API naming conventions and standards (paths, schema/property names, tags). 

---

## How Copilot should work (process)

- **Before proposing changes**, search the repo for existing components/headers/parameters/responses to **reuse**. If a near‑match exists, refactor to reference it rather than duplicating. 
- **When creating/updating** an API:
  - Start from the template below and **fill every description**.
  - Ensure `servers.url` includes the version segment (e.g., `https://api.example.com/v1`).
  - Add a `tags` entry and ensure each operation references a tag.
  - Include `/health`, `/health/readiness`, and `/health/liveness`.
  - Apply OAuth 2.0 security (see template).
  - Reference standard headers from `components.headers`.
  - Prefer `$ref` to `components` for request/response bodies and parameters.
- **Before finalizing**, run a self‑check using the Golden Rules checklist in this file.

---

## OpenAPI Starter Template (use this)

> Replace placeholders (`TODO:`) and keep comments as needed until review passes. Ensure **every field** has a description.

```yaml
openapi: "3.0.2"  # must be 3.0.2 or higher 
info:
  title: "TODO: 8–50 char functional title aligned to BIAN taxonomy"  
  version: "1.0.0"  # semantic version of spec
  description: |
    TODO: Clear functional summary.
    - Prerequisites / Dependencies: TODO list upstream/downstream systems.
    - Internal snapshot: TODO high-level internal flow so consumers know what's happening.
  termsOfService: "https://TODO/terms"  # include if applicable
  contact:
    name: "TODO: Owning team or individual"
    email: "TODO: team-or-owner@example.com"  # team email preferred
externalDocs:
  description: "Further documentation and runbooks"
  url: "https://TODO/wiki-or-runbook"  
tags:
  - name: "TODO:PrimaryTag"
    description: "Purpose/domain (BIAN-aligned)"  
servers:
  - url: "https://api.example.com/v1"  # must include /v1 style segment  
    description: "Production server"
  - url: "https://sandbox.example.com/v1"
    description: "Sandbox server"

security:
  - oauth2: [read, write]  # at least one security scheme required  

paths:
  /health:
    get:
      summary: "Liveness and basic health"
      description: "Returns overall health information."
      tags: ["Operations"]  # must reference an existing tag  
      responses:
        "200":
          description: "Service is healthy"
  /health/readiness:
    get:
      summary: "Readiness probe"
      description: "Indicates whether the service is ready to handle traffic."
      tags: ["Operations"]
      responses:
        "200":
          description: "Service is ready"
  /health/liveness:
    get:
      summary: "Liveness probe"
      description: "Indicates whether the service is alive."
      tags: ["Operations"]
      responses:
        "200":
          description: "Service is alive"

  /TODO/resource:
    get:
      summary: "TODO: concise operation summary"
      description: "TODO: detailed description of what this does."
      tags: ["TODO:PrimaryTag"]  
      parameters:
        - $ref: "#/components/parameters/CorrelationId"
        - name: "id"
          in: "query"
          required: false
          description: "Resource identifier to filter results."  
          schema: { type: "string" }
      security:
        - oauth2: [read]
      responses:
        "200":
          description: "Successful response with resource list."
          headers:
            X-Correlation-ID:
              $ref: "#/components/headers/X-Correlation-ID"
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/TODOResourceList"
        "400": { $ref: "#/components/responses/BadRequest" }
        "401": { $ref: "#/components/responses/Unauthorized" }
        "403": { $ref: "#/components/responses/Forbidden" }
        "404": { $ref: "#/components/responses/NotFound" }
        "429": { $ref: "#/components/responses/TooManyRequests" }
        "500": { $ref: "#/components/responses/InternalServerError" }

components:
  securitySchemes:
    oauth2:  # OAuth 2.0 required
      type: oauth2
      description: "OAuth 2.0 with authorizationCode or clientCredentials."
      flows:
        authorizationCode:
          authorizationUrl: "https://auth.example.com/oauth/authorize"
          tokenUrl: "https://auth.example.com/oauth/token"
          scopes:
            read: "Read access"
            write: "Write access"
  headers:
    Authorization:
      description: "Bearer access token in the form `Authorization: Bearer <token>`." 
      schema: { type: "string" }
    X-Correlation-ID:
      description: "Correlation identifier for end-to-end tracing (UUID recommended)." 
      schema: { type: "string", format: "uuid" }
  parameters:
    CorrelationId:
      name: "X-Correlation-ID"
      in: "header"
      required: false
      description: "Client-supplied correlation ID; if omitted, the service may generate one." 
      schema: { type: "string", format: "uuid" }
  responses:
    BadRequest:
      description: "Request could not be understood or was missing required parameters."
      content:
        application/json:
          schema: { $ref: "#/components/schemas/ProblemDetails" }
    Unauthorized:
      description: "Authentication failed or was not provided."
    Forbidden:
      description: "Authenticated but not authorized."
    NotFound:
      description: "Resource not found."
    TooManyRequests:
      description: "Rate limit exceeded."
    InternalServerError:
      description: "Unexpected server error."
  schemas:
    TODOResourceList:
      type: "object"
      description: "Container for a list of TODO resources."
      properties:
        items:
          type: "array"
          description: "The list of resources."
          items:
            $ref: "#/components/schemas/TODOResource"
    TODOResource:
      type: "object"
      description: "A TODO resource."
      properties:
        id:
          type: "string"
          description: "Unique identifier."
        name:
          type: "string"
          description: "Human-readable name."
    ProblemDetails:
      type: "object"
      description: "RFC 7807 problem details structure."
      properties:
        type:        { type: "string", description: "Problem type URI." }
        title:       { type: "string", description: "Short, human-readable summary." }
        status:      { type: "integer", description: "HTTP status code." }
        detail:      { type: "string", description: "Detailed error message." }
        instance:    { type: "string", description: "URI reference to the specific occurrence." }
