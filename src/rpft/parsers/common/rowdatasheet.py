import networkx as nx
import tablib


class RowDataSheet:
    def __init__(self, row_parser, rows, target_headers=set(), excluded_headers=set()):
        """
        Class to export list of models to spreadsheet.

        Note: If the model supports remapping where multiple fields of different
        types are mapped to the same column header, that column header needs to
        be specified in target_headers.

        Args:
            rows (list[ParserModel]): a list of RowModel instances
            row_parser (RowParser): parser to use for converting rows to flat dicts.
            target_headers (set[str]): Complex type fields (ParserModels, lists, dicts)
                whose content should be represented in the output as single columns.
                A trailing asterisk may be used to specify multiple fields at once,
                such as `list.*` and `field.*`.
            excluded_headers (set[str]): Fields to exclude from the output. Same format
                as target_headers.
        """
        self.row_parser = row_parser
        self.rows = rows
        self.target_headers = target_headers
        self.excluded_headers = excluded_headers

    def export(self, filename, file_format="csv"):
        """
        Export a list of RowModel instances to file.

        Args:
            filename: destination filename
            format: Export file format.
                Supported file formats as supported by tablib,
                see https://tablib.readthedocs.io/en/stable/formats.html
        """
        data = self.convert_to_tablib()
        exported_data = data.export(file_format)
        if type(exported_data) is str:
            # There is a strange bug where on Windows, csv files would get
            # exported with \r\r\n linebreaks. The below fixes this.
            exported_data = exported_data.replace("\r", "")
            exported_data = exported_data.encode("utf-8")
        with open(filename, "wb") as f:
            f.write(exported_data)

    def convert_to_tablib(self):
        """
        Convert a list of RowModel instances to tablib.Dataset.

        Return:
          A tablib.Dataset representation of the data.
        """

        data = tablib.Dataset()
        data.headers = self._get_headers()
        for row in self.rows:
            row_dict = self.row_parser.unparse_row(
                row, self.target_headers, self.excluded_headers
            )
            data.append([row_dict.get(header, "") for header in data.headers])
        return data

    def _get_headers(self):
        """
        Get an ordered list of column headers.
        Each row contains a subset of the final set of column headers.
        These subsets need to be merged while respecting the relative order
        within each row. Note: The resulting set of headers is unique,
        however, their order is not guaranteed to be unique.
        TODO: A better approach would be to use the DataModel of the rows
        to uniquely infer the order of the headers.
        Return:
            A list of strings representing the column headers of the sheet.
        """

        # Create a graph (representing a poset) whose nodes are the column headers,
        # and whose edges A -> B represent that column header A should come before
        # column header B.
        header_graph = nx.DiGraph()
        for row in self.rows:
            row_dict = self.row_parser.unparse_row(
                row, self.target_headers, self.excluded_headers
            )
            k_prev = None
            # For each pair of consecutive headers in this row, add an edge.
            for k, _ in row_dict.items():
                if k_prev:
                    header_graph.add_edge(k_prev, k)
                k_prev = k

        # We now get a linear order of our headers from this poset graph
        # by doing a topological sort.
        try:
            ordering = list(nx.topological_sort(header_graph))
        except nx.exception.NetworkXUnfeasible:
            raise ValueError("Inconsistent ordering of headers in provided rows.")
        return ordering
