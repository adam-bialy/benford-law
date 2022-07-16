from flask import Flask, render_template, request, redirect, Markup
from methods import UserDistribution, StoredDistribution, open_file, get_datasets, clear_temp_storage


app = Flask(__name__)


@app.route("/", methods=["GET"])
def get():
    clear_temp_storage()
    return render_template("index.html")


@app.route("/load", methods=["POST"])
def load():
    file = request.files['datafile']
    filename = "storage/"+file.filename
    try:
        file.save(filename)
    except IsADirectoryError:
        return redirect("/")
    df = open_file(filename)
    columns = df.columns
    table = df.head()
    table = Markup(table.to_html())
    return render_template("index.html", show_form=True, columns=columns, table=table, filename=filename)


@app.route("/plot", methods=["POST"])
def plot():
    col = request.form['column']
    filename = request.form['filename']
    df = open_file(filename)
    columns = df.columns
    table = df.head()
    table = Markup(table.to_html())
    try:
        distribution = UserDistribution(df, col)
    except (ValueError, TypeError):
        error = f"Selected dataset ({col}) cannot be analyzed in this way"
        return render_template("index.html", show_form=True, columns=columns, error=error,
                               table=table, filename=filename)
    except KeyError:
        error = "Please choose an existing column"
        return render_template("index.html", show_form=True, columns=columns, error=error,
                               table=table, filename=filename)
    result = distribution.benford_test()
    fig_html = distribution.create_plot_figure()
    result_dict = {True: "conforms", False: "does not conform"}
    commit_instruction = f"Commit first digit distribution in {col} from {filename.split('/')[-1]} to database."
    return render_template("index.html", show_form=True, columns=columns, table=table,
                           result="{:.3f}".format(result), figure=fig_html, col=col, filename=filename,
                           verdict=result_dict[result < 1.330], instruction=commit_instruction)


@app.route("/commit", methods=["POST"])
def commit():
    col = request.form['column']
    filename = request.form['filename']
    df = open_file(filename)
    distribution = UserDistribution(df, col)
    name = f"{col}-{filename.split('/')[-1]}"
    distribution.commit_dataset(name)
    return redirect("/")


@app.route("/datasets", methods=["GET"])
def show_datasets():
    clear_temp_storage()
    datasets = get_datasets()
    size = len(datasets)
    return render_template("database.html", datasets=datasets, size=size)


@app.route("/datasets", methods=["POST"])
def plot_dataset():
    datasets = get_datasets()
    size = len(datasets)
    try:
        _id = request.form["dataset"]
    except KeyError:
        return redirect("/datasets")
    try:
        dataset = StoredDistribution(_id)
    except FileNotFoundError:
        return redirect("/datasets")
    result = dataset.benford_test()
    fig_html = dataset.create_plot_figure()
    result_dict = {True: "conforms", False: "does not conform"}
    return render_template("database.html", datasets=datasets, size=size, result="{:.3f}".format(result),
                           verdict=result_dict[result < 1.330], name=dataset.name, figure=fig_html)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8000)
