from typing import List, Tuple, Dict

class PokerHandEvaluator:
    def __init__(self):
        self.valor_cartas = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, 
                           '8': 8, '9': 9, '10': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
        self.nombres_manos = {
            10: "Escalera Real",
            9: "Escalera de Color",
            8: "Póker",
            7: "Full House",
            6: "Color",
            5: "Escalera",
            4: "Trio",
            3: "Doble Pareja",
            2: "Pareja",
            1: "Carta Alta"
        }
    
    def evaluar_mano(self, mano: List[str], comunidad: List[str]) -> Tuple[int, List[int], str]:
        """
        Evalúa una mano de poker y retorna:
        - ranking (1-10)
        - valores de desempate
        - nombre de la mano
        """
        todas_las_cartas = mano + comunidad
        valores = [self.obtener_valor(carta) for carta in todas_las_cartas]
        palos = [self.obtener_palo(carta) for carta in todas_las_cartas]
        
        # Ordenar valores de mayor a menor
        valores.sort(reverse=True)
        
        # Verificar todas las combinaciones posibles
        resultados = []
        
        # Escalera Real
        real = self._es_escalera_real(valores, palos)
        if real:
            return 10, real, self.nombres_manos[10]
        
        # Escalera de Color
        escalera_color = self._es_escalera_color(valores, palos)
        if escalera_color:
            return 9, escalera_color, self.nombres_manos[9]
        
        # Póker
        poker = self._es_poker(valores)
        if poker:
            return 8, poker, self.nombres_manos[8]
        
        # Full House
        full = self._es_full_house(valores)
        if full:
            return 7, full, self.nombres_manos[7]
        
        # Color
        color = self._es_color(palos, valores)
        if color:
            return 6, color, self.nombres_manos[6]
        
        # Escalera
        escalera = self._es_escalera(valores)
        if escalera:
            return 5, escalera, self.nombres_manos[5]
        
        # Trio
        trio = self._es_trio(valores)
        if trio:
            return 4, trio, self.nombres_manos[4]
        
        # Doble Pareja
        doble_pareja = self._es_doble_pareja(valores)
        if doble_pareja:
            return 3, doble_pareja, self.nombres_manos[3]
        
        # Pareja
        pareja = self._es_pareja(valores)
        if pareja:
            return 2, pareja, self.nombres_manos[2]
        
        # Carta Alta
        return 1, self._carta_alta(valores), self.nombres_manos[1]
    
    def obtener_valor(self, carta: str) -> int:
        """Extrae el valor numérico de una carta"""
        valor = carta[:-1]  # Remover el palo
        return self.valor_cartas[valor]
    
    def obtener_palo(self, carta: str) -> str:
        """Extrae el palo de una carta"""
        return carta[-1]
    
    def _es_escalera_real(self, valores: List[int], palos: List[str]) -> List[int]:
        """Verifica si hay escalera real (10-J-Q-K-A del mismo palo)"""
        for palo in set(palos):
            cartas_del_palo = [valores[i] for i in range(len(valores)) if palos[i] == palo]
            if len(cartas_del_palo) >= 5:
                cartas_del_palo.sort(reverse=True)
                if set([10, 11, 12, 13, 14]).issubset(set(cartas_del_palo)):
                    return [14]  # Siempre gana
        return None
    
    def _es_escalera_color(self, valores: List[int], palos: List[str]) -> List[int]:
        """Verifica si hay escalera de color"""
        for palo in set(palos):
            cartas_del_palo = [valores[i] for i in range(len(valores)) if palos[i] == palo]
            if len(cartas_del_palo) >= 5:
                escalera = self._encontrar_escalera(cartas_del_palo)
                if escalera:
                    return [escalera[0]]  # Retorna la carta más alta de la escalera
        return None
    
    def _es_poker(self, valores: List[int]) -> List[int]:
        """Verifica si hay póker (4 cartas del mismo valor)"""
        contador = self._contar_valores(valores)
        for valor, count in contador.items():
            if count >= 4:
                # Retorna [valor del póker, kicker]
                kicker = max([v for v in valores if v != valor])
                return [valor, kicker]
        return None
    
    def _es_full_house(self, valores: List[int]) -> List[int]:
        """Verifica si hay full house (trio + pareja)"""
        contador = self._contar_valores(valores)
        trios = [v for v, c in contador.items() if c >= 3]
        parejas = [v for v, c in contador.items() if c >= 2 and v not in trios]
        
        if trios and parejas:
            mejor_trio = max(trios)
            mejor_pareja = max(parejas)
            return [mejor_trio, mejor_pareja]
        elif len(trios) >= 2:
            # Dos trios - el mayor es el trio, el menor es la pareja
            trios.sort(reverse=True)
            return [trios[0], trios[1]]
        return None
    
    def _es_color(self, palos: List[str], valores: List[int]) -> List[int]:
        """Verifica si hay color (5 cartas del mismo palo)"""
        for palo in set(palos):
            cartas_del_palo = [valores[i] for i in range(len(valores)) if palos[i] == palo]
            if len(cartas_del_palo) >= 5:
                cartas_del_palo.sort(reverse=True)
                return cartas_del_palo[:5]  # Retorna las 5 cartas más altas
        return None
    
    def _es_escalera(self, valores: List[int]) -> List[int]:
        """Verifica si hay escalera (5 cartas consecutivas)"""
        escalera = self._encontrar_escalera(valores)
        if escalera:
            return [escalera[0]]  # Retorna la carta más alta de la escalera
        return None
    
    def _es_trio(self, valores: List[int]) -> List[int]:
        """Verifica si hay trio (3 cartas del mismo valor)"""
        contador = self._contar_valores(valores)
        trios = [v for v, c in contador.items() if c >= 3]
        if trios:
            mejor_trio = max(trios)
            # Retorna [valor del trio, kicker1, kicker2]
            kickers = [v for v in valores if v != mejor_trio]
            kickers.sort(reverse=True)
            return [mejor_trio] + kickers[:2]
        return None
    
    def _es_doble_pareja(self, valores: List[int]) -> List[int]:
        """Verifica si hay doble pareja"""
        contador = self._contar_valores(valores)
        parejas = [v for v, c in contador.items() if c >= 2]
        if len(parejas) >= 2:
            parejas.sort(reverse=True)
            # Retorna [mejor pareja, segunda pareja, kicker]
            kickers = [v for v in valores if v not in parejas[:2]]
            kickers.sort(reverse=True)
            return parejas[:2] + [kickers[0] if kickers else 0]
        return None
    
    def _es_pareja(self, valores: List[int]) -> List[int]:
        """Verifica si hay pareja (2 cartas del mismo valor)"""
        contador = self._contar_valores(valores)
        parejas = [v for v, c in contador.items() if c >= 2]
        if parejas:
            mejor_pareja = max(parejas)
            # Retorna [valor de la pareja, kicker1, kicker2, kicker3]
            kickers = [v for v in valores if v != mejor_pareja]
            kickers.sort(reverse=True)
            return [mejor_pareja] + kickers[:3]
        return None
    
    def _carta_alta(self, valores: List[int]) -> List[int]:
        """Retorna las 5 cartas más altas"""
        valores_unicos = list(set(valores))
        valores_unicos.sort(reverse=True)
        return valores_unicos[:5]
    
    def _contar_valores(self, valores: List[int]) -> Dict[int, int]:
        """Cuenta la frecuencia de cada valor"""
        contador = {}
        for valor in valores:
            contador[valor] = contador.get(valor, 0) + 1
        return contador
    
    def _encontrar_escalera(self, valores: List[int]) -> List[int]:
        """Encuentra la escalera más alta en una lista de valores"""
        valores_unicos = sorted(set(valores))
        
        # Verificar escalera normal
        for i in range(len(valores_unicos) - 4, -1, -1):
            if valores_unicos[i+4] - valores_unicos[i] == 4:
                return list(range(valores_unicos[i+4], valores_unicos[i]-1, -1))
        
        # Verificar escalera baja (A-2-3-4-5)
        if set([14, 2, 3, 4, 5]).issubset(set(valores_unicos)):
            return [5, 4, 3, 2, 14]  # El 5 es la carta alta en escalera baja
        
        return None
    
    def comparar_manos(self, mano1: Tuple[int, List[int]], mano2: Tuple[int, List[int]]) -> int:
        """
        Compara dos manos de poker
        Retorna: 1 si mano1 gana, -1 si mano2 gana, 0 si empate
        """
        ranking1, valores1, _ = mano1
        ranking2, valores2, _ = mano2
        
        if ranking1 > ranking2:
            return 1
        elif ranking1 < ranking2:
            return -1
        else:
            # Mismo ranking, comparar valores de desempate
            for v1, v2 in zip(valores1, valores2):
                if v1 > v2:
                    return 1
                elif v1 < v2:
                    return -1
            return 0