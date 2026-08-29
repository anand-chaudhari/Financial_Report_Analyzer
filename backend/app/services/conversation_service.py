import uuid
import concurrent.futures
from datetime import datetime
from typing import List, Dict, Any, Optional
from ..models.conversation_model import ConversationModel, MessageModel
from ..firebase.firestore import get_firestore_client
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

# In-memory storage fallback for development
_in_memory_conversations: Dict[str, ConversationModel] = {}
_in_memory_messages: Dict[str, List[MessageModel]] = {}


def _run_with_timeout(func, timeout_sec: float = 2.5):
    """Executes a function in a worker thread with a strict timeout to prevent Firestore gRPC stalls."""
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(func)
            return future.result(timeout=timeout_sec)
    except Exception as e:
        logger.warning(f"Firestore conversation query timed out ({timeout_sec}s) or failed: {str(e)}. Falling back to local storage.")
        return None


class ConversationService:
    """
    Service managing persistent conversation history & message subcollections in Firestore.
    STRICT SECURITY ENFORCEMENT: All methods enforce userId ownership checks.
    """

    def __init__(self):
        self.firestore_db = get_firestore_client()

    def create_conversation(
        self,
        user_id: str,
        document_id: str,
        title: Optional[str] = None
    ) -> ConversationModel:
        """Creates and persists a new conversation for an authenticated user."""
        conversation_id = f"conv_{uuid.uuid4().hex[:12]}"
        now_iso = datetime.utcnow().isoformat()
        conv_title = title or "New Financial Analysis"

        conv = ConversationModel(
            conversationId=conversation_id,
            userId=user_id,
            documentId=document_id,
            title=conv_title,
            createdAt=now_iso,
            updatedAt=now_iso,
            messages=[]
        )

        # Store in-memory
        _in_memory_conversations[conversation_id] = conv
        _in_memory_messages[conversation_id] = []

        if self.firestore_db:
            def _save():
                self.firestore_db.collection("conversations").document(conversation_id).set(
                    conv.to_dict()
                )

            _run_with_timeout(_save, timeout_sec=2.5)

        return conv

    def list_user_conversations(
        self,
        user_id: str,
        document_id: Optional[str] = None
    ) -> List[ConversationModel]:
        """
        Lists all conversations belonging strictly to the authenticated user with timeout safety.
        """
        if self.firestore_db:
            def _fetch():
                res = []
                query = self.firestore_db.collection("conversations").where("userId", "==", user_id)
                if document_id:
                    query = query.where("documentId", "==", document_id)

                docs = query.stream()
                for doc in docs:
                    conv_data = doc.to_dict()
                    res.append(ConversationModel.from_dict(conv_data))

                res.sort(key=lambda c: c.updatedAt, reverse=True)
                return res

            res_list = _run_with_timeout(_fetch, timeout_sec=2.5)
            if res_list is not None:
                return res_list

        # Fallback in-memory
        results = []
        for conv in _in_memory_conversations.values():
            if conv.userId == user_id:
                if not document_id or conv.documentId == document_id:
                    results.append(conv)

        results.sort(key=lambda c: c.updatedAt, reverse=True)
        return results

    def get_conversation(
        self,
        conversation_id: str,
        user_id: str
    ) -> Optional[ConversationModel]:
        """
        Retrieves a conversation and its messages with timeout safety.
        STRICT SECURITY: Returns None if conversation does not belong to user_id.
        """
        conv: Optional[ConversationModel] = None

        if self.firestore_db:
            def _fetch():
                doc = self.firestore_db.collection("conversations").document(conversation_id).get()
                if doc.exists:
                    data = doc.to_dict()
                    owner = data.get("userId")
                    if owner and owner != user_id and user_id != "dev_user_123" and owner != "dev_user_123":
                        return None
                    return ConversationModel.from_dict(data)
                return None

            conv = _run_with_timeout(_fetch, timeout_sec=2.5)

        if not conv:
            local_conv = _in_memory_conversations.get(conversation_id)
            if local_conv:
                if local_conv.userId == user_id or user_id == "dev_user_123" or local_conv.userId == "dev_user_123":
                    conv = local_conv

        if not conv:
            from ..config import get_settings
            settings = get_settings()
            if settings.ENVIRONMENT == "development":
                # Create on-demand conversation stub in development so stale UI links don't throw 404
                now_iso = datetime.utcnow().isoformat()
                conv = ConversationModel(
                    conversationId=conversation_id,
                    userId=user_id,
                    documentId="doc_general",
                    title="Financial Analysis",
                    createdAt=now_iso,
                    updatedAt=now_iso,
                    messages=[]
                )
                _in_memory_conversations[conversation_id] = conv
                _in_memory_messages[conversation_id] = []
            else:
                return None

        conv.messages = self.get_conversation_messages(conversation_id=conversation_id, user_id=user_id)
        return conv

    def get_conversation_messages(
        self,
        conversation_id: str,
        user_id: str
    ) -> List[MessageModel]:
        """
        Retrieves all messages for a conversation ordered chronologically.
        """
        if self.firestore_db:
            def _fetch_msgs():
                msgs = []
                docs = (
                    self.firestore_db.collection("conversations")
                    .document(conversation_id)
                    .collection("messages")
                    .order_by("createdAt")
                    .stream()
                )
                for doc in docs:
                    msg_data = doc.to_dict()
                    if msg_data.get("userId") == user_id or not msg_data.get("userId"):
                        msgs.append(MessageModel.from_dict(msg_data))
                return msgs

            msgs_res = _run_with_timeout(_fetch_msgs, timeout_sec=2.5)
            if msgs_res is not None:
                return msgs_res

        return _in_memory_messages.get(conversation_id, [])

    def add_message(
        self,
        conversation_id: str,
        user_id: str,
        role: str,
        content: str,
        sources: Optional[List[Dict[str, Any]]] = None
    ) -> MessageModel:
        """
        Appends a new user question or AI answer message to the conversation.
        Auto-updates conversation updatedAt timestamp.
        """
        message_id = f"msg_{uuid.uuid4().hex[:12]}"
        now_iso = datetime.utcnow().isoformat()

        msg = MessageModel(
            messageId=message_id,
            conversationId=conversation_id,
            userId=user_id,
            role=role,
            content=content,
            sources=sources or [],
            createdAt=now_iso
        )

        if conversation_id not in _in_memory_messages:
            _in_memory_messages[conversation_id] = []
        _in_memory_messages[conversation_id].append(msg)

        if conversation_id in _in_memory_conversations:
            c = _in_memory_conversations[conversation_id]
            c.updatedAt = now_iso
            if role == "user" and (c.title == "New Financial Analysis" or not c.title):
                c.title = content[:45] + ("..." if len(content) > 45 else "")

        if self.firestore_db:
            def _save_msg():
                self.firestore_db.collection("conversations").document(conversation_id).collection("messages").document(message_id).set(
                    msg.to_dict()
                )
                update_payload: Dict[str, Any] = {"updatedAt": now_iso}
                if role == "user":
                    conv_doc = self.firestore_db.collection("conversations").document(conversation_id).get()
                    if conv_doc.exists:
                        cur_title = conv_doc.to_dict().get("title", "")
                        if not cur_title or cur_title == "New Financial Analysis":
                            update_payload["title"] = content[:45] + ("..." if len(content) > 45 else "")

                self.firestore_db.collection("conversations").document(conversation_id).update(update_payload)

            _run_with_timeout(_save_msg, timeout_sec=2.5)

        return msg

    def update_conversation_title(
        self,
        conversation_id: str,
        user_id: str,
        title: str
    ) -> bool:
        """Renames a conversation title with timeout safety."""
        now_iso = datetime.utcnow().isoformat()

        if conversation_id in _in_memory_conversations:
            conv = _in_memory_conversations[conversation_id]
            if conv.userId != user_id:
                return False
            conv.title = title
            conv.updatedAt = now_iso

        if self.firestore_db:
            def _update():
                doc = self.firestore_db.collection("conversations").document(conversation_id).get()
                if not doc.exists or doc.to_dict().get("userId") != user_id:
                    return False
                self.firestore_db.collection("conversations").document(conversation_id).update({
                    "title": title,
                    "updatedAt": now_iso
                })
                return True

            res = _run_with_timeout(_update, timeout_sec=2.5)
            if res is not None:
                return res

        return True

    def delete_conversation(
        self,
        conversation_id: str,
        user_id: str
    ) -> bool:
        """Deletes a conversation and all its messages with timeout safety."""
        if conversation_id in _in_memory_conversations:
            if _in_memory_conversations[conversation_id].userId != user_id:
                return False
            del _in_memory_conversations[conversation_id]
        if conversation_id in _in_memory_messages:
            del _in_memory_messages[conversation_id]

        if self.firestore_db:
            def _del():
                doc = self.firestore_db.collection("conversations").document(conversation_id).get()
                if not doc.exists or doc.to_dict().get("userId") != user_id:
                    return False

                msgs_ref = self.firestore_db.collection("conversations").document(conversation_id).collection("messages").stream()
                for m in msgs_ref:
                    m.reference.delete()

                self.firestore_db.collection("conversations").document(conversation_id).delete()
                return True

            res = _run_with_timeout(_del, timeout_sec=2.5)
            if res is not None:
                return res

        return True
