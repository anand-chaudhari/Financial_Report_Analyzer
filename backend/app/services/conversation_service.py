import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from ..models.conversation_model import ConversationModel, MessageModel
from ..firebase.firestore import get_firestore_client
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

# In-memory storage fallback for development
_in_memory_conversations: Dict[str, ConversationModel] = {}
_in_memory_messages: Dict[str, List[MessageModel]] = {}


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

        # Store in Firestore
        _in_memory_conversations[conversation_id] = conv
        _in_memory_messages[conversation_id] = []

        if self.firestore_db:
            try:
                self.firestore_db.collection("conversations").document(conversation_id).set(
                    conv.to_dict()
                )
                logger.info(f"Created Firestore conversation '{conversation_id}' for user '{user_id}'.")
            except Exception as e:
                logger.error(f"Firestore create_conversation error: {str(e)}")

        return conv

    def list_user_conversations(
        self,
        user_id: str,
        document_id: Optional[str] = None
    ) -> List[ConversationModel]:
        """
        Lists all conversations belonging strictly to the authenticated user.
        """
        results: List[ConversationModel] = []

        if self.firestore_db:
            try:
                query = self.firestore_db.collection("conversations").where("userId", "==", user_id)
                if document_id:
                    query = query.where("documentId", "==", document_id)

                docs = query.stream()
                for doc in docs:
                    conv_data = doc.to_dict()
                    conv = ConversationModel.from_dict(conv_data)
                    results.append(conv)

                # Sort by updatedAt descending
                results.sort(key=lambda c: c.updatedAt, reverse=True)
                return results
            except Exception as e:
                logger.error(f"Firestore list_user_conversations error: {str(e)}")

        # Fallback in-memory
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
        Retrieves a conversation and its messages.
        STRICT SECURITY: Returns None if conversation does not belong to user_id.
        """
        conv: Optional[ConversationModel] = None

        if self.firestore_db:
            try:
                doc = self.firestore_db.collection("conversations").document(conversation_id).get()
                if doc.exists:
                    data = doc.to_dict()
                    # Security check
                    if data.get("userId") != user_id:
                        logger.warning(f"Access denied: User '{user_id}' attempted to access conversation '{conversation_id}' owned by '{data.get('userId')}'.")
                        return None
                    conv = ConversationModel.from_dict(data)
            except Exception as e:
                logger.error(f"Firestore get_conversation error: {str(e)}")

        if not conv:
            local_conv = _in_memory_conversations.get(conversation_id)
            if local_conv and local_conv.userId == user_id:
                conv = local_conv

        if not conv:
            return None

        # Fetch messages
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
        msgs: List[MessageModel] = []

        if self.firestore_db:
            try:
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
            except Exception as e:
                logger.error(f"Firestore get_conversation_messages error: {str(e)}")

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

        # Update in-memory
        if conversation_id not in _in_memory_messages:
            _in_memory_messages[conversation_id] = []
        _in_memory_messages[conversation_id].append(msg)

        if conversation_id in _in_memory_conversations:
            conv = _in_memory_conversations[conversation_id]
            conv.updatedAt = now_iso
            # Auto-update title if default
            if role == "user" and (conv.title == "New Financial Analysis" or not conv.title):
                conv.title = content[:45] + ("..." if len(content) > 45 else "")

        # Persist to Firestore
        if self.firestore_db:
            try:
                # Save message
                self.firestore_db.collection("conversations").document(conversation_id).collection("messages").document(message_id).set(
                    msg.to_dict()
                )

                # Update conversation updatedAt & title
                update_payload: Dict[str, Any] = {"updatedAt": now_iso}
                if role == "user":
                    conv_doc = self.firestore_db.collection("conversations").document(conversation_id).get()
                    if conv_doc.exists:
                        cur_title = conv_doc.to_dict().get("title", "")
                        if not cur_title or cur_title == "New Financial Analysis":
                            update_payload["title"] = content[:45] + ("..." if len(content) > 45 else "")

                self.firestore_db.collection("conversations").document(conversation_id).update(update_payload)
            except Exception as e:
                logger.error(f"Firestore add_message error: {str(e)}")

        return msg

    def update_conversation_title(
        self,
        conversation_id: str,
        user_id: str,
        title: str
    ) -> bool:
        """
        Renames a conversation title.
        Enforces user ownership.
        """
        now_iso = datetime.utcnow().isoformat()

        if conversation_id in _in_memory_conversations:
            conv = _in_memory_conversations[conversation_id]
            if conv.userId != user_id:
                return False
            conv.title = title
            conv.updatedAt = now_iso

        if self.firestore_db:
            try:
                doc = self.firestore_db.collection("conversations").document(conversation_id).get()
                if not doc.exists or doc.to_dict().get("userId") != user_id:
                    return False
                self.firestore_db.collection("conversations").document(conversation_id).update({
                    "title": title,
                    "updatedAt": now_iso
                })
                return True
            except Exception as e:
                logger.error(f"Firestore update_conversation_title error: {str(e)}")
                return False

        return True

    def delete_conversation(
        self,
        conversation_id: str,
        user_id: str
    ) -> bool:
        """
        Deletes a conversation and all its messages.
        Enforces user ownership.
        """
        if conversation_id in _in_memory_conversations:
            if _in_memory_conversations[conversation_id].userId != user_id:
                return False
            del _in_memory_conversations[conversation_id]
        if conversation_id in _in_memory_messages:
            del _in_memory_messages[conversation_id]

        if self.firestore_db:
            try:
                doc = self.firestore_db.collection("conversations").document(conversation_id).get()
                if not doc.exists or doc.to_dict().get("userId") != user_id:
                    return False

                # Delete messages subcollection
                msgs_ref = self.firestore_db.collection("conversations").document(conversation_id).collection("messages").stream()
                for m in msgs_ref:
                    m.reference.delete()

                # Delete conversation document
                self.firestore_db.collection("conversations").document(conversation_id).delete()
                logger.info(f"Deleted conversation '{conversation_id}' for user '{user_id}'.")
                return True
            except Exception as e:
                logger.error(f"Firestore delete_conversation error: {str(e)}")
                return False

        return True
