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
async def cmd_pasta(message: Message):
    # Simple logic for now, will enhance in Phase 3
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("Uso: /pasta <nome_da_pasta>")
        return
        
    folder_name = args[1].strip()
    
    async with await get_db() as db:
        await db.execute(
            "INSERT OR REPLACE INTO user_settings (user_id, current_folder) VALUES (?, ?)",
            (message.from_user.id, folder_name)
        )
        await db.commit()
        
    await message.reply(f"📁 Os próximos arquivos enviados por você serão organizados na pasta: `{folder_name}`")
