# Students Database CRUD API

A student-record management backend built for the EWB Edu Tech internship assignment using **Python, FastAPI, and SQLite**.

## Features

- Create, list, retrieve, fully replace, partially update, and delete student records.
- SQLite persistence; the database is created automatically on startup.
- Automatically generated unique integer student IDs.
- Required name and date of birth; at least one contact method (email or phone).
- Duplicate-email protection and useful HTTP errors for missing records.
- Filter by partial name, course, date of birth, and paginate with `limit`/`offset`.
- Interactive Swagger UI at `/docs` and OpenAPI schema at `/openapi.json`.
- Uses dummy/example data only. The optional Ollama bonus is not included because it is not required.

## Requirements

- Python 3.10 or newer
- pip

## Install and run

### Windows (PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn main:app --reload
```

If PowerShell blocks activation, run `python -m pip install -r requirements.txt` using your normal Python environment, then run `python -m uvicorn main:app --reload`.

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
uvicorn main:app --reload
```

Open <http://127.0.0.1:8000/docs> to test all endpoints in your browser. SQLite file `students.db` is created next to `main.py` at startup and is intentionally excluded from Git.

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/students` | Create a student |
| `GET` | `/students` | List/filter students |
| `GET` | `/students/{student_id}` | Retrieve one student |
| `PUT` | `/students/{student_id}` | Replace all editable fields |
| `PATCH` | `/students/{student_id}` | Update only supplied fields |
| `DELETE` | `/students/{student_id}` | Delete a student |

### Example requests

Create a student (`POST /students`):

```json
{
  "name": "Aarav Sharma",
  "date_of_birth": "2005-04-18",
  "email": "aarav@example.com",
  "phone": "+91-9876543210",
  "course": "Computer Science",
  "address": "Kolkata, India",
  "enrollment_date": "2024-08-01"
}
```

List students: `GET /students`

Filter: `GET /students?name=aarav&course=computer&born_after=2005-01-01`

Retrieve: `GET /students/1`

Partial update (`PATCH /students/1`):

```json
{"course": "Artificial Intelligence and Machine Learning"}
```

Delete: `DELETE /students/1` (returns `204 No Content`).

## Expected behavior / status codes

- `201 Created`: record created.
- `200 OK`: list, retrieve, or update succeeded.
- `204 No Content`: record deleted.
- `404 Not Found`: requested student ID does not exist.
- `409 Conflict`: duplicate email address.
- `422 Unprocessable Entity`: invalid input or missing contact methods.
- `400 Bad Request`: PATCH contains no fields.

## Data model

`student_id` (auto-generated primary key), `name`, `date_of_birth`, `email`, `phone`, `course`, `address`, `enrollment_date`, and `created_at`.


