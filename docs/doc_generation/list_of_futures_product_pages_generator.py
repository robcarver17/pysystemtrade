from pathlib import Path
from syscore.fileutils import resolve_path_and_filename_for_package
from docs.doc_generation.symbol_product_page_map import symbol_product_page_map

# GET ABSOLUTE PATH TO THE DOCS MODULE
file_in_module_where_md_file_is_to_be_stored = "docs.__init__.py"
full_path = resolve_path_and_filename_for_package(
    path_and_filename=file_in_module_where_md_file_is_to_be_stored
)
write_path = Path(full_path).parent

# ENSURE THAT MAPPING IS ALPAHBETICAL
symbols_list = list(symbol_product_page_map.keys())
symbols_list.sort()

with open(str(write_path / "list_of_futures_product_pages.md"), "w") as f:

    f.writelines(f"# List of futures product pages")
    f.writelines("\n")
    f.writelines(
        "Below is an incomplete mapping of instrument symbols to their corresponding futures product webpages. List will get updated in the future \n"
    )
    f.writelines(
        "Could be useful for checking price spikes, or for chekcing volumes and open interest when trying to decide what a good time to roll is. \n"
    )
    f.writelines(
        "CME has detailed graphs that go back several days. Other exchanges have detailed intra-day graphs.\n"
    )
    f.writelines(
        "Exceptions exist - like japanese pages - no price / chart data available at all. and also to look at volumes and open interest when rolling.\n"
    )
    f.writelines("\n")
    f.writelines("\n")

    for symbol in symbols_list:
        page = symbol_product_page_map[symbol]
        f.writelines(f"- {symbol}: [{page}]({page})\n")
