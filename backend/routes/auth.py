from flask import Blueprint, request, jsonify
from models import Usuario
from services.otp import crear_otp, verificar_otp
from services.whatsapp import enviar_mensaje_whatsapp
from config import Config

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/solicitar-otp', methods=['POST'])
def solicitar_otp():
    data = request.get_json(silent=True) or {}
    telefono = data.get('telefono', '').strip()

    if not telefono:
        return jsonify({'error': 'El campo telefono es requerido'}), 400

    try:
        usuario = Usuario.get(Usuario.telefono == telefono)
    except Usuario.DoesNotExist:
        return jsonify({'error': 'Usuario no encontrado'}), 404

    if not usuario.activo:
        return jsonify({'error': 'Usuario inactivo'}), 403

    try:
        validacion = crear_otp(usuario)
        mensaje = (
            f"Hola {usuario.nombre}, tu código de verificación es: *{validacion.codigo}*\n"
            f"Válido por {Config.OTP_EXPIRY_MINUTES} minutos. No lo compartas con nadie."
        )
        enviar_mensaje_whatsapp(usuario.telefono, mensaje)
        return jsonify({'success': True, 'mensaje': 'Código OTP enviado por WhatsApp'}), 200
    except Exception as e:
        return jsonify({'error': 'Error al enviar OTP', 'detalle': str(e)}), 500


@auth_bp.route('/verificar-otp', methods=['POST'])
def verificar_otp_route():
    data = request.get_json(silent=True) or {}
    telefono = data.get('telefono', '').strip()
    codigo = data.get('codigo', '').strip()

    if not telefono or not codigo:
        return jsonify({'error': 'Los campos telefono y codigo son requeridos'}), 400

    try:
        usuario = Usuario.get(Usuario.telefono == telefono)
    except Usuario.DoesNotExist:
        return jsonify({'error': 'Usuario no encontrado'}), 404

    valido, mensaje_resultado = verificar_otp(usuario, codigo)

    if valido:
        return jsonify({
            'success': True,
            'mensaje': mensaje_resultado,
            'usuario': {'id': usuario.id, 'nombre': usuario.nombre},
        }), 200

    return jsonify({'success': False, 'error': mensaje_resultado}), 401
