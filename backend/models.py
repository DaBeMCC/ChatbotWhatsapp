import datetime
from peewee import (
    MySQLDatabase, Model, CharField, TextField, DateTimeField,
    BooleanField, ForeignKeyField, AutoField
)
from config import Config

database = MySQLDatabase(
    Config.DB_NAME,
    host=Config.DB_HOST,
    port=Config.DB_PORT,
    user=Config.DB_USER,
    password=Config.DB_PASSWORD,
    charset='utf8mb4',
    autoconnect=False,
)


class BaseModel(Model):
    class Meta:
        database = database


class Usuario(BaseModel):
    id = AutoField()
    telefono = CharField(max_length=20, unique=True)
    nombre = CharField(max_length=100)
    email = CharField(max_length=150, unique=True, null=True)
    activo = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.datetime.now)

    class Meta:
        table_name = 'usuarios'


class ValidacionLogin(BaseModel):
    id = AutoField()
    usuario = ForeignKeyField(Usuario, backref='validaciones', on_delete='CASCADE')
    codigo = CharField(max_length=6)
    expiracion = DateTimeField()
    usado = BooleanField(default=False)
    created_at = DateTimeField(default=datetime.datetime.now)

    class Meta:
        table_name = 'validaciones_login'


class MantenimientoTaller(BaseModel):
    id = AutoField()
    usuario = ForeignKeyField(Usuario, backref='mantenimientos', on_delete='CASCADE')
    descripcion = TextField()
    fecha_cita = DateTimeField()
    recordatorio_24h_enviado = BooleanField(default=False)
    recordatorio_1h_enviado = BooleanField(default=False)
    cancelado = BooleanField(default=False)
    created_at = DateTimeField(default=datetime.datetime.now)

    class Meta:
        table_name = 'mantenimientos_taller'


def crear_tablas():
    with database.connection_context():
        database.create_tables(
            [Usuario, ValidacionLogin, MantenimientoTaller],
            safe=True
        )
