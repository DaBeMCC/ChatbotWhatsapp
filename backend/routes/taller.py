import datetime
from flask import Blueprint, request, jsonify
from models import Usuario, MantenimientoTaller

taller_bp = Blueprint('taller', __name__, url_prefix='/taller')


@taller_bp.route('/citas', methods=['POST'])
def crear_cita():
    data = request.get_json(silent=True) or {}
    usuario_id = data.get('usuario_id')
    descripcion = data.get('descripcion', '').strip()
    fecha_cita_str = data.get('fecha_cita', '').strip()

    if not all([usuario_id, descripcion, fecha_cita_str]):
        return jsonify({'error': 'usuario_id, descripcion y fecha_cita son requeridos'}), 400

    try:
        usuario = Usuario.get_by_id(usuario_id)
    except Usuario.DoesNotExist:
        return jsonify({'error': 'Usuario no encontrado'}), 404

    try:
        fecha_cita = datetime.datetime.fromisoformat(fecha_cita_str)
    except ValueError:
        return jsonify({
            'error': 'Formato de fecha inválido. Use ISO 8601: YYYY-MM-DDTHH:MM:SS'
        }), 400

    if fecha_cita <= datetime.datetime.now():
        return jsonify({'error': 'La fecha de cita debe ser en el futuro'}), 400

    cita = MantenimientoTaller.create(
        usuario=usuario,
        descripcion=descripcion,
        fecha_cita=fecha_cita,
    )

    return jsonify({
        'success': True,
        'cita': {
            'id': cita.id,
            'usuario_id': usuario.id,
            'descripcion': cita.descripcion,
            'fecha_cita': cita.fecha_cita.isoformat(),
            'created_at': cita.created_at.isoformat(),
        },
    }), 201


@taller_bp.route('/citas/usuario/<int:usuario_id>', methods=['GET'])
def listar_citas(usuario_id):
    try:
        usuario = Usuario.get_by_id(usuario_id)
    except Usuario.DoesNotExist:
        return jsonify({'error': 'Usuario no encontrado'}), 404

    citas = (MantenimientoTaller
             .select()
             .where(
                 (MantenimientoTaller.usuario == usuario) &
                 (MantenimientoTaller.cancelado == False)
             )
             .order_by(MantenimientoTaller.fecha_cita.asc()))

    return jsonify({
        'citas': [
            {
                'id': c.id,
                'descripcion': c.descripcion,
                'fecha_cita': c.fecha_cita.isoformat(),
                'recordatorio_24h_enviado': c.recordatorio_24h_enviado,
                'recordatorio_1h_enviado': c.recordatorio_1h_enviado,
            }
            for c in citas
        ]
    }), 200


@taller_bp.route('/citas/<int:cita_id>', methods=['DELETE'])
def cancelar_cita(cita_id):
    try:
        cita = MantenimientoTaller.get_by_id(cita_id)
    except MantenimientoTaller.DoesNotExist:
        return jsonify({'error': 'Cita no encontrada'}), 404

    if cita.cancelado:
        return jsonify({'error': 'La cita ya estaba cancelada'}), 409

    cita.cancelado = True
    cita.save()

    return jsonify({'success': True, 'mensaje': 'Cita cancelada correctamente'}), 200
