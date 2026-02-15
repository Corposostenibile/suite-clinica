"""
REST API endpoints for SOP Chatbot.
"""
import os
import threading
from pathlib import Path

from flask import current_app, jsonify, request
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from corposostenibile.extensions import db
from corposostenibile.models import SOPDocument
from ..services.document_service import DocumentService
from ..services.chat_service import ChatService
from ..services.qdrant_service import QdrantService

ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.doc'}


def _get_upload_dir():
    base = current_app.config.get('UPLOAD_FOLDER',
                                  str(Path(current_app.root_path).parent / 'uploads'))
    sop_dir = os.path.join(base, 'sop_documents')
    os.makedirs(sop_dir, exist_ok=True)
    return sop_dir


def register_api_routes(bp):

    @bp.route('/documents', methods=['GET'])
    @login_required
    def list_documents():
        docs = SOPDocument.query.order_by(SOPDocument.created_at.desc()).all()
        return jsonify({
            'success': True,
            'documents': [d.to_dict() for d in docs],
        })

    @bp.route('/documents/upload', methods=['POST'])
    @login_required
    def upload_document():
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'Nessun file inviato'}), 400

        file = request.files['file']
        if not file.filename:
            return jsonify({'success': False, 'error': 'Nome file vuoto'}), 400

        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            return jsonify({
                'success': False,
                'error': f'Tipo file non supportato. Formati accettati: {", ".join(ALLOWED_EXTENSIONS)}',
            }), 400

        filename = secure_filename(file.filename)
        upload_dir = _get_upload_dir()
        file_path = os.path.join(upload_dir, filename)

        # Avoid overwriting
        base_name = Path(filename).stem
        counter = 1
        while os.path.exists(file_path):
            filename = f"{base_name}_{counter}{ext}"
            file_path = os.path.join(upload_dir, filename)
            counter += 1

        file.save(file_path)
        file_size = os.path.getsize(file_path)

        mime_map = {'.pdf': 'application/pdf', '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', '.doc': 'application/msword'}

        doc = SOPDocument(
            filename=file.filename,
            file_path=file_path,
            file_size=file_size,
            mime_type=mime_map.get(ext, 'application/octet-stream'),
            status='processing',
            uploaded_by=current_user.id,
        )
        db.session.add(doc)
        db.session.commit()

        # Process in background thread
        app = current_app._get_current_object()

        def _process():
            with app.app_context():
                DocumentService.process_document(file_path, doc.id)

        thread = threading.Thread(target=_process, daemon=True)
        thread.start()

        return jsonify({
            'success': True,
            'document': doc.to_dict(),
            'message': 'Documento caricato. Elaborazione in corso...',
        }), 201

    @bp.route('/documents/<int:doc_id>', methods=['DELETE'])
    @login_required
    def delete_document(doc_id):
        doc = db.session.get(SOPDocument, doc_id)
        if not doc:
            return jsonify({'success': False, 'error': 'Documento non trovato'}), 404

        DocumentService.delete_document(doc_id)
        return jsonify({'success': True, 'message': 'Documento eliminato'})

    @bp.route('/chat', methods=['POST'])
    @login_required
    def chat():
        data = request.get_json()
        if not data or not data.get('query'):
            return jsonify({'success': False, 'error': 'Query mancante'}), 400

        query = data['query'].strip()
        session_id = data.get('session_id', f"user_{current_user.id}_sop")

        result = ChatService.ask(query, session_id)

        return jsonify({
            'success': True,
            'response': result['response'],
            'sources': result['sources'],
            'session_id': result['session_id'],
        })

    @bp.route('/chat/clear', methods=['POST'])
    @login_required
    def clear_chat():
        data = request.get_json() or {}
        session_id = data.get('session_id', f"user_{current_user.id}_sop")
        ChatService.clear_session(session_id)
        return jsonify({'success': True, 'message': 'Sessione pulita'})

    @bp.route('/stats', methods=['GET'])
    @login_required
    def stats():
        total_docs = SOPDocument.query.count()
        ready_docs = SOPDocument.query.filter_by(status='ready').count()
        total_chunks = QdrantService.get_total_chunks()

        return jsonify({
            'success': True,
            'stats': {
                'total_documents': total_docs,
                'ready_documents': ready_docs,
                'total_chunks': total_chunks,
            },
        })
