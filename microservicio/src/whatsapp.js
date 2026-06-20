import makeWASocket, {
  DisconnectReason,
  fetchLatestBaileysVersion,
  makeCacheableSignalKeyStore,
  useMultiFileAuthState,
} from '@whiskeysockets/baileys';
import pino from 'pino';
import qrcode from 'qrcode-terminal';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const AUTH_DIR = path.join(__dirname, '../../auth_info');
const TIMEOUT_CONEXION_MS = 120_000;

const logger = pino({ level: 'warn' });

let sock = null;
let estaConectado = false;
let resolversConexion = [];

async function conectar() {
  const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);
  const { version } = await fetchLatestBaileysVersion();

  sock = makeWASocket({
    version,
    auth: {
      creds: state.creds,
      keys: makeCacheableSignalKeyStore(state.keys, logger),
    },
    logger,
    printQRInTerminal: false,
    generateHighQualityLinkPreview: false,
    getMessage: async () => ({ conversation: '' }),
  });

  sock.ev.on('connection.update', ({ connection, lastDisconnect, qr }) => {
    if (qr) {
      console.log('\n[WhatsApp] Escanea el QR para vincular tu cuenta:\n');
      qrcode.generate(qr, { small: true });
    }

    if (connection === 'open') {
      console.log('[WhatsApp] ✓ Conexión establecida correctamente.');
      estaConectado = true;
      resolversConexion.forEach(({ resolve }) => resolve());
      resolversConexion = [];
    }

    if (connection === 'close') {
      estaConectado = false;
      const statusCode = lastDisconnect?.error?.output?.statusCode;
      const debeReconectar = statusCode !== DisconnectReason.loggedOut;

      console.log(
        `[WhatsApp] Conexión cerrada. Código: ${statusCode ?? 'desconocido'}. ` +
        `Reconectar: ${debeReconectar}`
      );

      resolversConexion.forEach(({ reject }) =>
        reject(new Error(`Conexión cerrada con código ${statusCode}`))
      );
      resolversConexion = [];

      if (debeReconectar) {
        console.log('[WhatsApp] Reconectando en 5 segundos...');
        setTimeout(conectar, 5_000);
      } else {
        console.error(
          '[WhatsApp] ✗ Sesión cerrada permanentemente. ' +
          'Elimina la carpeta auth_info/ y reinicia el servicio para vincular de nuevo.'
        );
      }
    }
  });

  sock.ev.on('creds.update', saveCreds);
}

function esperarConexion() {
  if (estaConectado) return Promise.resolve();

  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      reject(new Error('Timeout: WhatsApp no conectó en el tiempo esperado.'));
    }, TIMEOUT_CONEXION_MS);

    resolversConexion.push({
      resolve: () => { clearTimeout(timer); resolve(); },
      reject: (err) => { clearTimeout(timer); reject(err); },
    });
  });
}

async function enviarMensaje(telefono, mensaje) {
  await esperarConexion();

  const numeroLimpio = telefono.replace(/[\s\-\+\(\)]/g, '');
  const jid = `${numeroLimpio}@s.whatsapp.net`;

  const resultado = await sock.sendMessage(jid, { text: mensaje });
  return resultado;
}

export { conectar, enviarMensaje, estaConectado };
