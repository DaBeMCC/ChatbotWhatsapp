import random
import string
import datetime
from models import ValidacionLogin, Usuario
from config import Config


def _generar_codigo() -> str:
    return ''.join(random.choices(string.digits, k=6))


def crear_otp(usuario: Usuario) -> ValidacionLogin:
    ValidacionLogin.update(usado=True).where(
        (ValidacionLogin.usuario == usuario) &
        (ValidacionLogin.usado == False)
    ).execute()

    expiracion = datetime.datetime.now() + datetime.timedelta(
        minutes=Config.OTP_EXPIRY_MINUTES
    )
    validacion = ValidacionLogin.create(
        usuario=usuario,
        codigo=_generar_codigo(),
        expiracion=expiracion,
        usado=False,
    )
    return validacion


def verificar_otp(usuario: Usuario, codigo: str) -> tuple[bool, str]:
    try:
        validacion = ValidacionLogin.get(
            (ValidacionLogin.usuario == usuario) &
            (ValidacionLogin.codigo == codigo) &
            (ValidacionLogin.usado == False)
        )
    except ValidacionLogin.DoesNotExist:
        return False, 'Código inválido'

    if datetime.datetime.now() > validacion.expiracion:
        return False, 'Código expirado'

    validacion.usado = True
    validacion.save()
    return True, 'Código válido'
