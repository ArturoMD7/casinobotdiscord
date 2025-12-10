from supabase import create_client, Client
import os
import logging

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE")

class Database:
    def __init__(self):
        self.client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    # ============================
    # GET SALDO
    # ============================
    def get_saldo(self, discord_id: str) -> int | None:
        """
        Devuelve el saldo de un usuario vinculado.
        """
        try:
            res = self.client.table("profiles")\
                .select("saldo")\
                .eq("discord_id", discord_id)\
                .maybe_single()\
                .execute()
            
            if res.data:
                return res.data["saldo"]
            return None
        except Exception as e:
            logger.error(f"Error en get_saldo: {e}")
            return None

    # ============================
    # UPDATE SALDO (CORREGIDO)
    # ============================
    def update_saldo(self, discord_id: str, amount: int, transaction_type="game", game_type="", details=""):
        """
        Actualiza saldo mediante RPC segura.
        """
        try:
            # Llamar a la función RPC
            res = self.client.rpc("increment_profile_saldo", {
                "p_discord_id": discord_id,
                "p_amount": amount
            }).execute()
            
            # En versiones recientes, res es una tupla o tiene diferente estructura
            # Verificamos si hubo éxito de diferentes maneras
            
            # Método 1: Verificar si hay datos o si es None
            if res is None:
                logger.error("RPC returned None")
                return False
                
            # Método 2: Verificar si es una respuesta exitosa (204 No Content es normal para RPC)
            # El RPC puede devolver 204 sin contenido, lo cual es exitoso
            
            # Registrar en historial (no bloquear si falla el historial)
            try:
                self.client.table("transactions_bot").insert({
                    "discord_id": discord_id,
                    "amount": amount,
                    "type": transaction_type,
                    "game_type": game_type,
                    "details": details
                }).execute()
            except Exception as hist_error:
                logger.warning(f"Error al registrar historial: {hist_error}")
                # No retornamos False porque el saldo sí se actualizó
            
            return True
            
        except Exception as e:
            logger.error(f"Error en update_saldo: {e}")
            return False

    # ============================
    # VINCULAR EMAIL ↔ DISCORD
    # ============================
    def link_discord_to_profile(self, discord_id: str, email: str):
        """
        Busca ese email en profiles y le asigna el discord_id.
        """
        try:
            res = self.client.table("profiles").select("id").eq("email", email).maybe_single().execute()

            if not res.data:
                return False  # No existe ese email

            self.client.table("profiles").update({
                "discord_id": discord_id
            }).eq("email", email).execute()

            return True
        except Exception as e:
            logger.error(f"Error en link_discord_to_profile: {e}")
            return False