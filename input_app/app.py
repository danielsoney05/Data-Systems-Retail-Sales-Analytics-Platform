from flask import Flask, render_template, request, redirect
import pandas as pd

app = Flask(__name__)
FILE_PATH = "data/merged_data.csv"

def load_data():
    return pd.read_csv(FILE_PATH)


# Form
@app.route("/")
def form():
    df = load_data()

    # Get sellers
    sellers = df[["seller_id", "seller_city", "seller_state"]].drop_duplicates()
    sellers = sellers.to_dict("records")

    fields = list(df.columns)

    return render_template("form.html", sellers=sellers, fields=fields)


# Handle submission
@app.route("/submit", methods=["POST"])
def submit():
    df = load_data()

    new_row = dict(request.form)

    # Append
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    df.to_csv(FILE_PATH, index=False)

    return redirect("/")



# Run app
if __name__ == "__main__":
    app.run(debug=True)