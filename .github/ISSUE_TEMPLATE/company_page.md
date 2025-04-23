## 🧩 Feature: [TAB NAME] Tab - Company Admin View

### 🎯 Goal
Implement the [TAB NAME] tab in the company dashboard. This view allows admins to manage and view key data related to [short description of the tab’s focus].

---

### 📁 View

#### `[TabName]View (class-based view)`
- **Context Data Required:**
  - [List all the necessary data from the database]
  - [Include filters/search context if applicable]
  - [Relationships like parent-child, tutor-children, etc.]

---

### 🧱 UI Components / Layout

- **Search & Filters:** (if applicable)
  - [Example: Search by parent name, filter by status]
- **Data Table or Grid:**
  - Columns: [List columns shown on screen]
  - Actions: [Edit, Deactivate, View Profile, etc.]
- **Stat Boxes or Widgets (optional):**
  - [Example: “Top 5 most active parents”]
- **Conditional Warnings or Notices:**
  - [Example: “3 parents haven't approved sessions in 7+ days”]
- **Quick Access Cards:** (optional)
  - [Example: Recent activity by parents]

---

### 🧠 UX Efficiency Notes
- Keep data sortable and paginated
- Include action buttons where applicable (view, edit, deactivate)
- Use alert colors/icons for pending statuses, warnings, etc.

---

### ✅ Done When:
- [ ] `[TabName]View` returns complete and efficient context data
- [ ] Template renders data with sorting, filtering, and pagination if needed
- [ ] All admin actions are functional (view, edit, toggle status, etc.)
- [ ] Empty states have placeholder messages (e.g., "No registered parents yet")
- [ ] Visual consistency with other dashboard tabs

---

📌 **Related Issues:**
- [Link to dashboard issue]
- [Link to model-related issues or context]
