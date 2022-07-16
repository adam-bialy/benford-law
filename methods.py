from os import path, remove, listdir
import numpy as np
import pandas as pd
from flask import Markup
from plotly import graph_objects as go
import sqlite3


class Benford:

    benford = pd.DataFrame({"n": [1, 2, 3, 4, 5, 6, 7, 8, 9]})
    benford["p"] = np.log10(1 + 1 / benford["n"])

    def benford_test(self):
        """
        Test whether a leading number distribution does not conform to Benford's law,
        according to Cho-Gaines / Morrow dN statistic.
        """
        d = np.sqrt(self.n) * np.sqrt(((self.distribution["p"] - self.benford["p"]) ** 2).sum())
        return d

    def create_plot_figure(self):
        """
        Plot the distribution.
        """
        fig = go.Figure()
        fig.add_bar(x=self.distribution['n'], y=self.distribution['p'], name="data")
        fig.add_bar(x=self.benford['n'], y=self.benford['p'], name="reference")
        fig.layout['barmode'] = "group"
        fig.layout['paper_bgcolor'] = "#FFE69A"
        fig.update_layout(xaxis_title="Number", yaxis_title="Frequency")
        fig.update_layout(font={"size": 15}, font_color="black")
        fig.update_layout(margin=dict(l=10, r=10, t=40, b=0))
        fig_html = Markup(fig.to_html(full_html=False))
        return fig_html


class UserDistribution(Benford):

    def __init__(self, df, col):
        """
        Obtain distribution of leading numbers from selected column in the dataframe.
        """
        series = df[col]
        series = series.dropna()
        series = series[series != 0.0]
        n = series.count()
        series = series.astype(np.float64)
        series = series.apply(self._get_leading)
        distribution = series.value_counts() / series.value_counts().sum()
        distribution = distribution.reset_index()
        distribution = distribution.rename(columns={col: "temp"})
        distribution = distribution.rename(columns={"index": "n"})
        distribution = pd.merge(distribution, self.benford['n'], on="n", how="outer")
        distribution = distribution.rename(columns={"temp": "p"})
        distribution["p"] = distribution["p"].fillna(0)
        distribution = distribution.sort_values("n")
        distribution = distribution.reset_index(drop=True)
        self.n = n
        self.distribution = distribution

    def commit_dataset(self, name):
        """
        Insert dataset distribution into the database.
        """
        data = self.distribution["p"].apply(lambda x: "{:.6f}".format(x))
        data = " ".join(data)
        conn = sqlite3.connect("benforddatabase.db")
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO benford_distributions (name, n, distr) VALUES (?, ?, ?)""",
                    (name, int(self.n), data))
        conn.commit()
        conn.close()

    @staticmethod
    def _get_leading(num):
        """
        Get leading digit from a number.
        """
        num = abs(num)
        num = np.format_float_scientific(num)
        return int(num[0])


class StoredDistribution(Benford):

    def __init__(self, _id):
        """
        Get dataset from database by ID.
        """
        conn = sqlite3.connect("benforddatabase.db")
        cur = conn.cursor()
        cur.execute("SELECT name, n, distr FROM benford_distributions WHERE id=?", (_id,))
        results = cur.fetchall()
        if results:
            name = results[0][0]
            n = results[0][1]
            df = pd.DataFrame({"n": [1, 2, 3, 4, 5, 6, 7, 8, 9]})
            df["p"] = [np.float64(i) for i in results[0][2].split()]
            conn.close()
            self.name = name
            self.n = n
            self.distribution = df
        else:
            conn.close()
            raise FileNotFoundError("Dataset with this ID does not exist.")


def open_file(filename):
    """
    Open uploaded file into pandas dataframe.
    """
    filepath = path.abspath(filename)
    df = pd.read_csv(filepath, sep=None, engine="python")
    return df


def get_datasets():
    """
    Retrieve the list of datasets in db for display.
    """
    conn = sqlite3.connect("benforddatabase.db")
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM benford_distributions")
    results = cur.fetchall()
    return results


def clear_temp_storage():
    """
    Clear storage of uploaded files.
    """
    for file in listdir("storage"):
        remove("storage/"+file)
