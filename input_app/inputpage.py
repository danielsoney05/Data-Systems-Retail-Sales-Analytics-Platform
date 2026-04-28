#THIS IS NOT THE MAIN APP, JUST A TESTING FILE FOR INPUTTING DATA VIA CONSOLE

import pandas as pd

FILE_PATH = "data/merged_data.csv"

# ----------------------------
# Load dataset
# ----------------------------
def load_data():
    try:
        df = pd.read_csv(FILE_PATH)
        return df
    except FileNotFoundError:
        print("❌ ERROR: merged_data.csv not found.")
        exit()


# ----------------------------
# Seller selection
# ----------------------------
def choose_seller(df):
    sellers = df[["seller_id", "seller_city", "seller_state"]].drop_duplicates()
    sellers_list = sellers.to_dict("records")

    if not sellers_list:
        print("⚠️ No sellers found. You will enter manually.")
        return None

    print("\n=== Select a Seller ===")
    display_limit = min(50, len(sellers_list))

    for i in range(display_limit):
        s = sellers_list[i]
        print(f"{i+1}. {s['seller_id']} ({s['seller_city']}, {s['seller_state']})")

    while True:
        try:
            choice = input("Enter number (or press Enter to skip): ")

            if choice == "":
                return None

            choice = int(choice) - 1
            if 0 <= choice < display_limit:
                return sellers_list[choice]

        except:
            pass

        print("Invalid choice, try again.")


# ----------------------------
# Input handler (basic validation)
# ----------------------------
def get_input(field):
    value = input(f"{field}: ")

    if value.strip() == "":
        return None

    # Simple numeric handling
    try:
        if any(x in field for x in ["price", "value", "lat", "lng", "weight", "cm"]):
            return float(value)

        if any(x in field for x in ["qty", "installments", "prefix", "length", "height", "width", "sequential"]):
            return int(value)

    except:
        print("⚠️ Invalid type, storing as text.")

    return value


# ----------------------------
# Main entry logic
# ----------------------------
def main():
    df = load_data()
    fields = list(df.columns)

    selected_seller = choose_seller(df)

    print("\n=== Enter Order Data ===")

    new_row = {}

    for field in fields:

        # Auto-fill seller fields if selected
        if selected_seller:
            if field == "seller_id":
                new_row[field] = selected_seller["seller_id"]
                continue
            elif field == "seller_city":
                new_row[field] = selected_seller["seller_city"]
                continue
            elif field == "seller_state":
                new_row[field] = selected_seller["seller_state"]
                continue

        new_row[field] = get_input(field)

    # Append new row
    new_df = pd.DataFrame([new_row])
    df = pd.concat([df, new_df], ignore_index=True)

    # Save
    df.to_csv(FILE_PATH, index=False)

    print("\n✅ Data successfully added to dataset!")


# ----------------------------
# Run program
# ----------------------------
if __name__ == "__main__":
    main()