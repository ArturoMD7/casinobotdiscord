import mysql.connector
from mysql.connector import Error
from config import DB_CONFIG, STARTING_CREDITS
import logging
import time

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.conn = None
        self.connect()

    def connect(self):
        """Conecta a la base de datos con reintentos"""
        max_retries = 3
        retry_delay = 2  # segundos
        
        for attempt in range(max_retries):
            try:
                self.conn = mysql.connector.connect(**DB_CONFIG)
                logger.info("✅ Conectado a la base de datos")
                return
            except Error as e:
                logger.error(f"❌ Error conectando a la base de datos (intento {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    raise  # Relanzar el error después de todos los intentos

    def ensure_connection(self):
        """Verifica y restablece la conexión si es necesario"""
        try:
            if self.conn is None or not self.conn.is_connected():
                logger.warning("🔌 Reconectando a la base de datos...")
                self.connect()
            return True
        except Error as e:
            logger.error(f"❌ Error en ensure_connection: {e}")
            raise

    def ensure_user(self, user_id: int):
        try:
            self.ensure_connection()
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT IGNORE INTO users (user_id, credits) 
                VALUES (%s, %s)
            """, (user_id, STARTING_CREDITS))
            self.conn.commit()
            cursor.close()
        except Error as e:
            logger.error(f"❌ Error asegurando usuario: {e}")
            self.conn.rollback()
            raise

    def get_credits(self, user_id: int) -> int:
        try:
            self.ensure_connection()
            self.ensure_user(user_id)
            cursor = self.conn.cursor()
            cursor.execute("SELECT credits FROM users WHERE user_id = %s", (user_id,))
            result = cursor.fetchone()
            cursor.close()
            return result[0] if result else STARTING_CREDITS
        except Error as e:
            logger.error(f"❌ Error obteniendo créditos: {e}")
            raise

    def update_credits(self, user_id: int, amount: int, transaction_type: str = "game", game_type: str = "", details: str = ""):
        try:
            self.ensure_connection()
            cursor = self.conn.cursor()
            
            # Actualizar créditos
            cursor.execute("UPDATE users SET credits = credits + %s WHERE user_id = %s", (amount, user_id))
            
            # Registrar transacción (si la tabla existe)
            try:
                cursor.execute("""
                    INSERT INTO transactions (user_id, type, amount, game_type, details)
                    VALUES (%s, %s, %s, %s, %s)
                """, (user_id, transaction_type, amount, game_type, details))
            except Error:
                pass  # Ignorar si la tabla de transacciones no existe
            
            # Actualizar estadísticas si es una apuesta
            if transaction_type in ['win', 'loss']:
                try:
                    if amount > 0:  # Ganancia
                        cursor.execute("""
                            UPDATE users SET 
                            games_won = games_won + 1,
                            total_winnings = total_winnings + %s,
                            games_played = games_played + 1
                            WHERE user_id = %s
                        """, (amount, user_id))
                    else:  # Pérdida
                        cursor.execute("""
                            UPDATE users SET games_played = games_played + 1 
                            WHERE user_id = %s
                        """, (user_id,))
                except Error:
                    pass  # Ignorar si las columnas de estadísticas no existen
            
            self.conn.commit()
            cursor.close()
            return True
        except Error as e:
            logger.error(f"❌ Error actualizando créditos: {e}")
            self.conn.rollback()
            raise

    def get_user_stats(self, user_id: int) -> dict:
        try:
            self.ensure_connection()
            cursor = self.conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT credits, games_played, games_won, total_winnings 
                FROM users WHERE user_id = %s
            """, (user_id,))
            stats = cursor.fetchone()
            cursor.close()
            return stats or {}
        except Error as e:
            logger.error(f"❌ Error obteniendo estadísticas: {e}")
            raise

    def save_blackjack_game(self, user_id: int, bet_amount: int, result: str, payout: int, player_hand: list, dealer_hand: list):
        try:
            self.ensure_connection()
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO blackjack_sessions (user_id, bet_amount, result, payout, player_hand, dealer_hand)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (user_id, bet_amount, result, payout, str(player_hand), str(dealer_hand)))
            self.conn.commit()
            cursor.close()
            return True
        except Error as e:
            logger.error(f"❌ Error guardando partida de blackjack: {e}")
            # No hacer rollback para no afectar la actualización de créditos
            raise

    def get_all_users(self) -> list:
        """Obtiene una lista de todos los user_ids en la base de datos"""
        try:
            self.cursor.execute("SELECT user_id FROM users")
            users = [row[0] for row in self.cursor.fetchall()]
            return users
        except Exception as e:
            print(f"Error getting all users: {e}")
            return []