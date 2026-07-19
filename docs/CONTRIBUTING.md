# ScaleFlow Frontend Contribution Guidelines

This guide details the coding standards and architectural rules for expanding the ScaleFlow user interface.

---

## 1. State Design Decision Rules

When introducing new states or properties, use the following guidelines:

### A. When to create a React Context Provider
- State is consumed globally across multiple layout boundaries (e.g. active workspace, document selections).
- State represents long-lived session configurations (e.g. notifications queue, dark theme).
- State is low-frequency (does not trigger updates multiple times per second).

### B. When to write a Custom Hook
- The logic involves stateful business decisions, database inquiries, or polling selectors.
- The behavior extracts or formats telemetry data from the store.
- **Hook return shape standard:**
  ```javascript
  return {
    data,     // Values and state variables
    loading,  // Operation loading state indicator
    error,    // Error context or null
    actions   // Callback action dispatchers
  };
  ```

### C. When to create a Presentational UI Component
- The view is presentation-only, logic-less, and relies exclusively on incoming props.
- It performs zero direct backend API requests or polling operations.
- It is styled solely with design tokens (`tokens.css`) or helper classes.

---

## 2. Naming Standards

Maintain consistent naming suffixes and casing schemas:

```text
src/
├── components/
│   ├── ui/
│   │   ├── Button.jsx            # Atomic Presentational (CamelCase)
│   │   └── Button.test.jsx
│   ├── workers/
│   │   ├── useWorkers.js         # Custom Hook (camelCase prefix 'use')
│   │   ├── WorkersPage.js        # Composition Root (CamelCase page suffix)
│   │   └── WorkerCard.jsx        # Presentation Card (CamelCase card suffix)
```

---

## 3. Style & Layout Conventions

- **No Inline Styles:** Do not use `style={{ ... }}` for layout settings or colors. Use spacing utility classes or variables from `components.css`.
- **Responsive Layout Classes:** Leverage mobile-first utility classes inside `responsive.css` to handle column wrap overrides (e.g. `.workspace-grid`, `.hide-mobile`).
