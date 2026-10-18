# Facilitated Review Feature – Specification

## 📦 Projeto “Macro – Hackathon iFood”

The repository located at **`/home/daniel/coisas/hackathon`** implements a **macro‑assistant** that guides a user through the whole iFood ordering flow:

| Layer | Main entry point | Purpose |
|-------|------------------|---------|
| **Backend** | `app/main.py` → FastAPI app | Provides the REST API (`/api/...`) that orchestrates the LLM, the mock iFood MCP service and the nutrition pipeline. |
| **Frontend** | `frontend/src/App.tsx` (Vite) | UI that mimics the iFood app – session creation, address selection, natural‑language search, item selection, checkout and a simple feedback textarea. |
| **Database** | `app/storage/database.py` (SQLite) | Persists sessions, orders and consumption history in `data/macro.sqlite3`. |
| **Skills / Orchestrator** | `app/agent/orchestrator.py` + `app/agent/skills.py` | Builds system prompts for the LLM, loads skill modules (e.g., `ifood_mcp`, `gemini`). |
| **Mock mode** | `IFOOD_MODE=mock` (default) | All iFood data are served from a static catalogue (`app/services/mock_ifood.py`). No real credentials are required.

The current checkout flow ends with a **feedback textarea** that is only stored locally in the frontend (it never reaches the backend). The new feature – *facilitated review* – will make this feedback a **first‑class, persisted review** attached to the order.

---

## 🎯 Goal
Create a **review‑facilitator** that:
1. Shows the user a lightweight, optional text input **during checkout**.
2. Sends the review to the backend together with the order confirmation.
3. Persists the review in the SQLite database alongside the order.
4. Returns the stored review in order‑detail responses so the frontend can display it in the *“Meu dia → Consumo”* view.
5. Works **both in mock and live modes** (in live mode the review is still stored locally because the iFood MCP does not expose a review endpoint).

---

## 🔧 Implementation Details

### 1. Database changes (`app/storage/database.py`)
* **Schema migration** – add a nullable `review TEXT` column to the `orders` table.  Perform an `ALTER TABLE` on startup if the column does not exist.
* **New method**:
  ```python
  def save_review(self, order_id: int, text: str) -> None:
      """Persist a short user review for a given order.
      ``text`` is trimmed to 200 characters before being saved.
      """
      self.conn.execute(
          "UPDATE orders SET review = ? WHERE id = ?",
          (text[:200], order_id),
      )
      self.conn.commit()
  ```
* **Include `review` in query results** – modify `get_order` / `list_orders` to fetch the column and expose it in the returned dict.

### 2. API changes (`app/api/endpoints/macro.py`)
* **Pydantic request model**:
  ```python
  class ReviewIn(BaseModel):
      order_id: int
      review: Optional[str] = None
  ```
* **Update checkout‑review endpoint** (`POST /api/checkout/review`):
  1. Validate the request with `ReviewIn`.
  2. If `review` is provided (non‑empty after stripping), call `db.save_review(order_id, review)`.
  3. Return the usual `OrderResponse` enriched with the optional `review` field.
* **Extend response model** (`OrderResponse` or equivalent) with:
  ```python
  review: Optional[str] = None
  ```
* Keep the endpoint **backward compatible** – callers that omit `review` continue to work unchanged.

### 3. Backend orchestration (no extra changes needed)
The orchestrator does not directly touch the checkout‑review endpoint, so no modifications are required there. The new field is purely data‑layer.

### 4. Frontend changes (React + TypeScript)
* **Component** – `CheckoutReview.tsx` (or the component that renders the final confirmation step):
  * Add a `useState<string>` called `reviewText`.
  * Render a `<textarea>` with:
    * `maxLength={200}`
    * placeholder: *“Deixe sua opinião sobre o pedido (opcional)”*.
    * a live character counter: `{reviewText.length}/200`.
  * When the user clicks **Confirmar pedido**, build the payload:
    ```ts
    const payload = {
        order_id: orderId,
        review: reviewText.trim() || undefined,
    };
    await api.post('/api/checkout/review', payload);
    ```
* **API typing** – update `api.ts` (or wherever the type for order responses lives) to include `review?: string`.
* **Order card UI** – `OrderCard.tsx` (used in the consumption list):
  ```tsx
  {order.review && (
      <p className="review">
          🗒️ <em>{order.review}</em>
      </p>
  )}
  ```
* **User guidance** – add a small tooltip next to the textarea explaining that the review is stored locally and will not be sent to iFood (because the MCP lacks that capability).

### 5. Tests
* **Unit test** – `tests/test_review_db.py` verifies that `save_review` updates the DB correctly and that `get_order` returns the stored review.
* **Integration test** – `tests/test_review_endpoint.py` uses FastAPI's `TestClient` to:
  1. POST to `/api/checkout/review` **with** a review and assert the response contains it.
  2. POST **without** a review and assert the order is still created and the `review` field is `null`.
* Run the full suite: `pytest -q`. Aim for ≥ 80 % coverage on the new routes.

### 6. Manual verification steps (post‑implementation)
1. Start the backend (`uvicorn app.main:create_app --host 127.0.0.1 --port 8000 --reload`).
2. Start the frontend (`npm run dev`).
3. Execute a full checkout flow, filling the review textarea.
4. After confirmation, navigate to *Meu dia → Consumo* and confirm the review is displayed under the order.
5. Repeat the flow leaving the textarea empty; ensure the order is still saved and no review is shown.

### 7. Deployment considerations
* The feature adds only a **local** column; no external services are required.
* In **live mode** the same endpoint will store the review locally because the iFood MCP does not expose a review endpoint – this keeps the system consistent across environments.
* No changes to environment variables are necessary.

---

## 📄 Deliverables
| File | Purpose |
|------|----------|
| `app/storage/database.py` | Schema migration, `save_review` method, query update. |
| `app/api/endpoints/macro.py` | New request/response models, endpoint logic. |
| `frontend/src/pages/CheckoutReview.tsx` (or similar) | UI textarea, state handling, payload assembly. |
| `frontend/src/components/OrderCard.tsx` | Render saved review. |
| `tests/test_review_db.py` | Unit test for DB layer. |
| `tests/test_review_endpoint.py` | Integration test for API. |
| `facilitated_review_spec.md` (this file) | Specification to be handed to another AI/developer. |

---

*This markdown fully describes the project context, the feature to be added, and concrete implementation steps. It can be given to an autonomous coding agent to implement the facilitated review functionality.*
