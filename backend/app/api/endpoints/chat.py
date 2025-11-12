"""
Chat API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List
import uuid
from datetime import datetime
from app.db.session import get_db
from app.schemas.chat import (
    ChatQueryRequest,
    ChatQueryResponse,
    ConversationCreate,
    Conversation as ConversationSchema,
    ChatMessage as ChatMessageSchema,
)
from app.services.query_engine import QueryEngine
from app.models.conversation import Conversation as ConversationModel, ChatMessage as ChatMessageModel

router = APIRouter()


@router.post("/query", response_model=ChatQueryResponse)
async def process_chat_query(
    request: ChatQueryRequest,
    db: Session = Depends(get_db)
):
    """Process a chat query using RAG"""
    try:
        # Get conversation history if conversation_id provided (from DB)
        conversation_history: List[dict] = []
        if request.conversation_id:
            msgs = (
                db.query(ChatMessageModel)
                .filter(ChatMessageModel.conversation_id == request.conversation_id)
                .order_by(ChatMessageModel.timestamp.asc())
                .all()
            )
            conversation_history = [
                {"role": m.role, "content": m.content, "timestamp": m.timestamp}
                for m in msgs
            ]

        # Process query
        query_engine = QueryEngine(db)
        response = await query_engine.process_query(
            query=request.query,
            fund_id=request.fund_id,
            document_ids=request.document_ids,
            conversation_history=conversation_history,
            weights=request.weights
        )

        # Update conversation history in DB
        if request.conversation_id:
            # Ensure conversation exists
            conv = db.query(ConversationModel).filter(ConversationModel.id == request.conversation_id).first()
            if not conv:
                conv = ConversationModel(
                    id=request.conversation_id,
                    fund_id=request.fund_id,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                db.add(conv)
                db.flush()
            # Append messages
            now = datetime.utcnow()
            db.add(ChatMessageModel(
                conversation_id=request.conversation_id,
                role="user",
                content=request.query,
                timestamp=now,
            ))
            db.add(ChatMessageModel(
                conversation_id=request.conversation_id,
                role="assistant",
                content=response["answer"],
                timestamp=now,
            ))
            conv.updated_at = now
            db.commit()

        return ChatQueryResponse(**response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process query: {str(e)}")


@router.post("/conversations", response_model=ConversationSchema)
async def create_conversation(request: ConversationCreate, db: Session = Depends(get_db)):
    """Create a new conversation"""
    conversation_id = str(uuid.uuid4())
    # Create in DB
    conv = ConversationModel(
        id=conversation_id,
        fund_id=request.fund_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    try:
        db.add(conv)
        db.commit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create conversation: {str(e)}")
    return ConversationSchema(
        conversation_id=conversation_id,
        fund_id=request.fund_id,
        messages=[],
        created_at=conv.created_at,
        updated_at=conv.updated_at,
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationSchema)
async def get_conversation(conversation_id: str):
    """Get conversation history"""
    db = next(get_db())
    try:
        conv = db.query(ConversationModel).filter(ConversationModel.id == conversation_id).first()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        msgs = (
            db.query(ChatMessageModel)
            .filter(ChatMessageModel.conversation_id == conversation_id)
            .order_by(ChatMessageModel.timestamp.asc())
            .all()
        )
        return ConversationSchema(
            conversation_id=conversation_id,
            fund_id=conv.fund_id,
            messages=[ChatMessageSchema(role=m.role, content=m.content, timestamp=m.timestamp) for m in msgs],
            created_at=conv.created_at,
            updated_at=conv.updated_at,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get conversation: {str(e)}")
    finally:
        db.close()


@router.get("/conversations", response_model=List[ConversationSchema])
async def list_conversations(
    fund_id: int = None,
    q: str = Query(None, description="Search text to filter conversations by message content"),
    db: Session = Depends(get_db),
):
    """List conversations (optionally filter by fund_id or search by message content)"""
    try:
        query = db.query(ConversationModel)
        if fund_id is not None:
            query = query.filter(ConversationModel.fund_id == fund_id)

        if q:
            # Join with ChatMessage to filter by content
            conv_ids = (
                db.query(ChatMessageModel.conversation_id)
                .filter(ChatMessageModel.content.ilike(f"%{q}%"))
                .distinct()
                .all()
            )
            conv_ids = [cid for (cid,) in conv_ids]
            if conv_ids:
                query = query.filter(ConversationModel.id.in_(conv_ids))
            else:
                return []

        # Sort by updated_at desc
        conversations = query.order_by(ConversationModel.updated_at.desc()).all()

        result: List[ConversationSchema] = []
        for conv in conversations:
            msgs = (
                db.query(ChatMessageModel)
                .filter(ChatMessageModel.conversation_id == conv.id)
                .order_by(ChatMessageModel.timestamp.asc())
                .all()
            )
            result.append(ConversationSchema(
                conversation_id=conv.id,
                fund_id=conv.fund_id,
                messages=[ChatMessageSchema(role=m.role, content=m.content, timestamp=m.timestamp) for m in msgs],
                created_at=conv.created_at,
                updated_at=conv.updated_at,
            ))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list conversations: {str(e)}")


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, db: Session = Depends(get_db)):
    """Delete a conversation and its messages"""
    try:
        conv = db.query(ConversationModel).filter(ConversationModel.id == conversation_id).first()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        # Delete messages then conversation
        db.query(ChatMessageModel).filter(ChatMessageModel.conversation_id == conversation_id).delete()
        db.delete(conv)
        db.commit()
        return {"message": "Conversation deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete conversation: {str(e)}")
