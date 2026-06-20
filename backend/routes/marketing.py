from flask import Blueprint, request, jsonify
from models import Usuario
from services.whatsapp import enviar_campana_whatsapp

marketing_bp = Blueprint('marketing', __name__, url_prefix='/marketing')


@marketing_bp.route('/campana', methods=['POST'])
def enviar_campana():
    data = request.get_json(silent=True) or {}
    mensaje_plantilla = data.get('mensaje', '').strip()
    usuarios_ids = data.get('usuarios_ids')

    if not mensaje_plantilla:
        return jsonify({'error': 'El campo mensaje es requerido'}), 400

    if not isinstance(usuarios_ids, list) or len(usuarios_ids) == 0:
        return jsonify({'error': 'usuarios_ids debe ser una lista no vacía'}), 400

    usuarios = (Usuario
                .select()
                .where(
                    (Usuario.id.in_(usuarios_ids)) &
                    (Usuario.activo == True)
                ))

    destinatarios = []
    for usuario in usuarios:
        mensaje_personalizado = mensaje_plantilla.replace('{nombre}', usuario.nombre)
        destinatarios.append({
            'telefono': usuario.telefono,
            'mensaje': mensaje_personalizado,
        })

    if not destinatarios:
        return jsonify({
            'error': 'No se encontraron usuarios activos con los IDs proporcionados'
        }), 404

    try:
        resultado = enviar_campana_whatsapp(destinatarios)
        return jsonify({
            'success': True,
            'total_encolados': len(destinatarios),
            'estado_cola': resultado,
        }), 202
    except Exception as e:
        return jsonify({'error': 'Error al encolar la campaña', 'detalle': str(e)}), 500
