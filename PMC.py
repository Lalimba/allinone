# Precious Metals Price Calculator
# Gold (karat-based) and Silver (percentage-based)

TROY_OUNCE_TO_GRAM = 31.1035

def price_per_gram(ounce_price, purity_percent):
    """
    ounce_price: price per troy ounce (USD, EUR, etc.)
    purity_percent: purity in percent (e.g. 75 for 18k gold)
    """
    pure_price_per_gram = ounce_price / TROY_OUNCE_TO_GRAM
    return pure_price_per_gram * (purity_percent / 100)


def gold_price_per_gram(ounce_price, karat):
    """
    karat: gold karat value (e.g. 24, 22, 21, 18)
    """
    purity_percent = (karat / 24) * 100
    return price_per_gram(ounce_price, purity_percent)


def silver_price_per_gram(ounce_price, purity_percent):
    """
    purity_percent: e.g. 99.9 for fine silver
    """
    return price_per_gram(ounce_price, purity_percent)


# ===== Example usage =====
if __name__ == "__main__":
    gold_ounce_price = float(input("Enter gold price per troy ounce: "))
    gold_karat = float(input("Enter gold karat (e.g. 24, 18): "))

    silver_ounce_price = float(input("Enter silver price per troy ounce: "))
    silver_purity = float(input("Enter silver purity in % (e.g. 99.9): "))

    gold_result = gold_price_per_gram(gold_ounce_price, gold_karat)
    silver_result = silver_price_per_gram(silver_ounce_price, silver_purity)

    print(f"\nGold ({gold_karat}k): {gold_result:.2f} per gram")
    print(f"Silver ({silver_purity}%): {silver_result:.2f} per gram")
