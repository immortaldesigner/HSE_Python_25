import requests

class FoodAPI:
    BASE_SEARCH_URL = "https://world.openfoodfacts.org/cgi/search.pl"
    BASE_BARCODE_URL = "https://world.openfoodfacts.org/api/v0/product"

    def __init__(self):
        pass

    def search_food(self, query: str, max_results: int = 5):
        params = {
            "search_terms": query,
            "search_simple": 1,
            "action": "process",
            "json": 1,
            "page_size": max_results
        }
        resp = requests.get(self.BASE_SEARCH_URL, params=params)
        data = resp.json()
        products = data.get("products", [])
        result = {"foods": {"food": []}}
        for p in products:
            name = p.get("product_name")
            calories = p.get("nutriments", {}).get("energy-kcal_100g")
            if calories is not None:
                calories = int(calories)
            result["foods"]["food"].append({
                "name": name or "Unknown",
                "calories": calories or 0,
                "id": p.get("id")
            })
        return result

    #Получение продукта по ID
    def get_food(self, food_id: str):
        return {"food": {"name": "Unknown", "calories": 0}}

    def get_by_barcode(self, barcode: str):
        url = f"{self.BASE_BARCODE_URL}/{barcode}.json"
        resp = requests.get(url)
        data = resp.json()
        product = data.get("product", {})
        name = product.get("product_name", "Unknown")
        calories = product.get("nutriments", {}).get("energy-kcal_100g")
        if calories is not None:
            calories = int(calories)
        return {"food": {"name": name, "calories": calories or 0}}
