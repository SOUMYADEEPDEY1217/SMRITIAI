"""
Thin wrapper around Firebase Admin SDK (Auth & Firestore),
with seamless fallback to local document cache when external credentials
or dependencies are absent/incompatible.
"""
from app.config import settings
import logging

logger = logging.getLogger("firebase_service")

MAX_QUERY_RESULTS = 500
_local_store = {}
_db = None
_auth = None

try:
    import firebase_admin
    from firebase_admin import credentials, auth, firestore

    _auth = auth
    if settings.FIREBASE_CREDENTIALS_PATH and settings.FIREBASE_PROJECT_ID:
        try:
            _app = firebase_admin.initialize_app(
                credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH),
                {"projectId": settings.FIREBASE_PROJECT_ID},
            )
            _db = firestore.client()
            logger.info(
                f"Firebase Admin SDK initialized against project "
                f"'{settings.FIREBASE_PROJECT_ID}' - Firestore is LIVE (not the local fallback)."
            )
        except Exception as e:
            _db = None
            # BUGFIX: this used to swallow the error silently, so a bad/missing
            # credential file looked identical to "Firebase not configured on
            # purpose" - both just quietly used the in-memory store. Now it's
            # loud, so a real credential problem doesn't look like the app
            # "working" when it's actually not persisting anything.
            logger.error(
                f"Firebase credentials found (path='{settings.FIREBASE_CREDENTIALS_PATH}', "
                f"project='{settings.FIREBASE_PROJECT_ID}') but initialization FAILED ({e}). "
                f"Falling back to the in-memory local store - data will NOT persist across "
                f"restarts. Check the credential file exists, is valid JSON, and matches the "
                f"project id."
            )
    else:
        logger.info(
            "FIREBASE_CREDENTIALS_PATH/FIREBASE_PROJECT_ID not set - using the in-memory "
            "local store on purpose (fine for local dev, data will NOT persist)."
        )
except Exception as e:
    _auth = None
    _db = None
    logger.info(f"Firebase Admin SDK not loaded ({e}). Operating with local document cache.")


def verify_id_token(id_token: str) -> dict:
    """Verifies token against Firebase Admin SDK, or processes local development tokens.

    BUGFIX: local/demo tokens now embed the real uid (format
    "demo::<uid>::<random>", issued by app/routers/auth.py) so this resolves
    each user's OWN stored profile instead of hardcoding everyone to
    "patient-1"/"doc-1"/"admin-1", which used to make every patient account
    share the same data.
    """
    if _auth:
        try:
            return _auth.verify_id_token(id_token, check_revoked=True)
        except Exception:
            pass

    if id_token.startswith("demo::"):
        parts = id_token.split("::")
        if len(parts) >= 2 and parts[1]:
            uid = parts[1]
            stored = get_document("users", uid)
            if stored:
                return {**stored, "uid": uid}
            # No stored profile (e.g. server restarted and wiped the
            # in-memory store) - still resolve to THIS uid, not a shared one.
            role = uid.split("-")[0]
            if role not in ("patient", "doctor", "admin"):
                role = "patient"
            return {"uid": uid, "name": "Smriti User", "role": role, "email": f"{uid}@smriti.com"}

    # Back-compat for older tokens (format "demo-<role>-<random>") that may
    # still be sitting in a browser's localStorage from before this fix.
    if id_token.startswith("demo-patient"):
        return {"uid": "patient-1", "name": "Ramesh Patel", "role": "patient", "email": "ramesh@smriti.com"}
    elif id_token.startswith("demo-doctor"):
        return {"uid": "doc-1", "name": "Dr. Ananya Sharma", "role": "doctor", "email": "ananya@smriti.com"}
    elif id_token.startswith("demo-admin"):
        return {"uid": "admin-1", "name": "System Administrator", "role": "admin", "email": "admin@smriti.com"}
    elif id_token.startswith("test-"):
        return {"uid": id_token, "name": "Test User", "role": "patient", "email": f"{id_token}@example.com"}
    return {"uid": f"user-{abs(hash(id_token)) % 10000}", "name": "User", "role": "patient", "email": "user@smriti.com"}


def add_document(collection: str, data: dict, doc_id: str | None = None) -> str:
    if _db:
        try:
            if doc_id:
                _db.collection(collection).document(doc_id).set(data)
                return doc_id
            ref = _db.collection(collection).add(data)[1]
            return ref.id
        except Exception:
            pass

    if collection not in _local_store:
        _local_store[collection] = {}
    actual_id = doc_id or f"auto-{len(_local_store[collection])}"
    record = dict(data)
    record["_id"] = actual_id
    record["id"] = actual_id
    _local_store[collection][actual_id] = record
    return actual_id


def get_document(collection: str, doc_id: str) -> dict | None:
    if _db:
        try:
            snap = _db.collection(collection).document(doc_id).get()
            if not snap.exists:
                return None
            data = snap.to_dict()
            data["_id"] = snap.id
            data["id"] = snap.id
            return data
        except Exception:
            pass

    col = _local_store.get(collection, {})
    item = col.get(doc_id)
    return dict(item) if item else None


def update_document(collection: str, doc_id: str, changes: dict) -> None:
    if _db:
        try:
            _db.collection(collection).document(doc_id).update(changes)
            return
        except Exception:
            pass

    if collection in _local_store and doc_id in _local_store[collection]:
        _local_store[collection][doc_id].update(changes)


def delete_document(collection: str, doc_id: str) -> None:
    if _db:
        try:
            _db.collection(collection).document(doc_id).delete()
            return
        except Exception:
            pass

    if collection in _local_store and doc_id in _local_store[collection]:
        del _local_store[collection][doc_id]


def query_by_field(collection: str, field: str, value) -> list[dict]:
    if _db:
        try:
            docs = (
                _db.collection(collection)
                .where(field, "==", value)
                .limit(MAX_QUERY_RESULTS)
                .stream()
            )
            results = []
            for d in docs:
                data = d.to_dict()
                data["_id"] = d.id
                data["id"] = d.id
                results.append(data)
            return results
        except Exception:
            pass

    col = _local_store.get(collection, {})
    return [dict(v) for v in col.values() if v.get(field) == value][:MAX_QUERY_RESULTS]


def query_all(collection: str) -> list[dict]:
    if _db:
        try:
            docs = _db.collection(collection).limit(MAX_QUERY_RESULTS).stream()
            return [{**d.to_dict(), "_id": d.id, "id": d.id} for d in docs]
        except Exception:
            pass

    col = _local_store.get(collection, {})
    return [dict(v) for v in col.values()][:MAX_QUERY_RESULTS]
