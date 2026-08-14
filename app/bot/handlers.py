from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from app.database.connection import get_db

router = Router(name="commands_router")

@router.message(Command("start", "help"))
async def cmd_start(message: Message):
    await message.reply(
        "👋 Olá! Sou o bot de ingestão de mídia.\n\n"
        "Envie vídeos, fotos ou documentos e eu os baixarei e organizarei automaticamente.\n\n"
        "Comandos:\n"
        "/status - Ver status da fila\n"
        "/pasta <nome> - Definir pasta de destino\n"
    )

@router.message(Command("pasta"))
@router.channel_post(Command("pasta"))
async def cmd_pasta(message: Message):
    text = message.text or message.caption
    if not text: return
    
    args = text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("Uso: /pasta <nome_da_pasta>")
        return
        
    folder_name = args[1].strip()
    
    # Em canais, message.from_user pode ser None
    user_id = message.from_user.id if message.from_user else 0
    
    async with get_db() as db:
        await db.execute(
            "INSERT OR REPLACE INTO user_settings (user_id, current_folder) VALUES (?, ?)",
            (user_id, folder_name)
        )
        await db.commit()
        
    await message.reply(f"📁 Os próximos arquivos enviados por você serão organizados na pasta: `{folder_name}`")

@router.message(Command("status"))
@router.channel_post(Command("status"))
async def cmd_status(message: Message):
    from app.database.queries import get_statistics
    stats = await get_statistics()
    
    total_mb = stats['total_bytes'] / (1024 * 1024)
    
    status_text = (
        "📊 **Dashboard Ingestor de Mídia**\n\n"
        f"✅ **Concluídos:** {stats['completed_files']} arquivos\n"
        f"⏳ **Na Fila/Baixando:** {stats['pending_files']} arquivos\n"
        f"❌ **Falhas:** {stats['failed_files']} arquivos\n"
        f"📁 **Total Baixado:** {total_mb:.2f} MB\n"
        f"📈 **Total Geral:** {stats['total_files']} arquivos recebidos\n\n"
        "Envie arquivos e o Ingestor processará tudo em background!"
    )
    
    await message.reply(status_text, parse_mode="Markdown")
