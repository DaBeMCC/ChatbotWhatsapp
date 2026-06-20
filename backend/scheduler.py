import datetime
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)


def _verificar_recordatorios(horas_offset: int, campo_flag: str, texto_tiempo: str):
    from models import database, MantenimientoTaller, Usuario
    from services.whatsapp import enviar_mensaje_whatsapp

    with database.connection_context():
        ahora = datetime.datetime.now()
        ventana_inicio = ahora + datetime.timedelta(hours=horas_offset, minutes=-5)
        ventana_fin = ahora + datetime.timedelta(hours=horas_offset, minutes=5)

        flag_field = getattr(MantenimientoTaller, campo_flag)

        citas = (MantenimientoTaller
                 .select(MantenimientoTaller, Usuario)
                 .join(Usuario)
                 .where(
                     (MantenimientoTaller.fecha_cita.between(ventana_inicio, ventana_fin)) &
                     (flag_field == False) &
                     (MantenimientoTaller.cancelado == False)
                 ))

        for cita in citas:
            try:
                usuario = cita.usuario
                fecha_str = cita.fecha_cita.strftime('%d/%m/%Y a las %H:%M')

                if horas_offset == 24:
                    mensaje = (
                        f"Hola {usuario.nombre}, te recordamos que tienes una cita de taller "
                        f"*mañana {fecha_str}*.\n\n"
                        f"Servicio: _{cita.descripcion}_\n\n"
                        f"Si necesitas cancelar o reagendar, contáctanos con anticipación."
                    )
                else:
                    mensaje = (
                        f"Hola {usuario.nombre}, tu cita de taller es *en {texto_tiempo}*, "
                        f"a las {cita.fecha_cita.strftime('%H:%M')}.\n\n"
                        f"Servicio: _{cita.descripcion}_\n\n"
                        f"¡Te esperamos!"
                    )

                enviar_mensaje_whatsapp(usuario.telefono, mensaje)

                (MantenimientoTaller
                 .update(**{campo_flag: True})
                 .where(MantenimientoTaller.id == cita.id)
                 .execute())

                logger.info(
                    "Recordatorio %s enviado para cita %d (usuario: %s)",
                    texto_tiempo, cita.id, usuario.telefono
                )
            except Exception as exc:
                logger.error(
                    "Error enviando recordatorio %s para cita %d: %s",
                    texto_tiempo, cita.id, exc
                )


def job_recordatorio_24h():
    _verificar_recordatorios(
        horas_offset=24,
        campo_flag='recordatorio_24h_enviado',
        texto_tiempo='24 horas',
    )


def job_recordatorio_1h():
    _verificar_recordatorios(
        horas_offset=1,
        campo_flag='recordatorio_1h_enviado',
        texto_tiempo='1 hora',
    )


def iniciar_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone='America/Mexico_City')

    scheduler.add_job(
        func=job_recordatorio_24h,
        trigger=IntervalTrigger(minutes=1),
        id='recordatorio_24h',
        name='Recordatorio citas 24 horas antes',
        replace_existing=True,
        misfire_grace_time=30,
    )

    scheduler.add_job(
        func=job_recordatorio_1h,
        trigger=IntervalTrigger(minutes=1),
        id='recordatorio_1h',
        name='Recordatorio citas 1 hora antes',
        replace_existing=True,
        misfire_grace_time=30,
    )

    scheduler.start()
    logger.info("APScheduler iniciado con 2 jobs de recordatorios.")
    return scheduler
