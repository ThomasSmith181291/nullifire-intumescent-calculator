"""
Export Nullifire product data from the legacy Access database to clean SQLite.
Run once to generate data/nullifire.db
"""
import sqlite3
import struct
import sys
import os

# We use the .NET OleDb via subprocess since pyodbc can't handle MDW workgroup security
# Instead, export via a C# helper. But first, let's try pyodbc with just the DB password.

def export_via_csharp():
    """Generate and run a C# exporter that uses OleDb with MDW auth."""
    cs_code = r'''
using System;
using System.Data;
using System.Data.OleDb;
using System.IO;
using System.Text;

class Exporter {
    static OleDbConnection OpenAccess() {
        string dbPath = @"C:\Users\Little Nineveh\AppData\Local\Nullifire Product Calculator\NulliLib.mdb";
        string mdwPath = @"C:\Users\Little Nineveh\AppData\Local\Nullifire Product Calculator\Vital Files\NulliSYS2000.MDW";
        string connStr = $"Jet OLEDB:Database Password='159$753';" +
                         $"Data Source='{dbPath}';" +
                         "Password=5896;" +
                         "Mode=Share Deny None;" +
                         "Jet OLEDB:Engine Type=5;" +
                         "Provider=Microsoft.Jet.OLEDB.4.0;" +
                         $"Jet OLEDB:System database='{mdwPath}';" +
                         "User ID=fpsi;";
        var conn = new OleDbConnection(connStr);
        conn.Open();
        return conn;
    }

    static void ExportTable(OleDbConnection src, StreamWriter w, string query, string csvName) {
        Console.WriteLine($"Exporting {csvName}...");
        using var cmd = new OleDbCommand(query, src);
        using var reader = cmd.ExecuteReader();

        // Header
        var cols = new string[reader.FieldCount];
        for (int i = 0; i < reader.FieldCount; i++) cols[i] = reader.GetName(i);
        w.WriteLine(string.Join("\t", cols));

        int rows = 0;
        while (reader.Read()) {
            var vals = new string[reader.FieldCount];
            for (int i = 0; i < reader.FieldCount; i++) {
                if (reader.IsDBNull(i)) vals[i] = "";
                else vals[i] = reader.GetValue(i).ToString().Replace("\t", " ").Replace("\n", " ").Replace("\r", "");
            }
            w.WriteLine(string.Join("\t", vals));
            rows++;
        }
        Console.WriteLine($"  {rows} rows");
    }

    static void Main(string[] args) {
        string outDir = args.Length > 0 ? args[0] : ".";
        using var src = OpenAccess();

        // 1. Steel Types
        using (var w = new StreamWriter(Path.Combine(outDir, "steel_types.tsv"), false, Encoding.UTF8))
            ExportTable(src, w, "SELECT SteelTypesID, SteelNames, Abbrev, CoverageBand, SortOrder FROM SteelTypes ORDER BY SortOrder", "SteelTypes");

        // 2. Steel Sizes (all origins)
        using (var w = new StreamWriter(Path.Combine(outDir, "steel_sizes.tsv"), false, Encoding.UTF8))
            ExportTable(src, w, "SELECT s.SteelSizesID, s.SerialSize, s.Depth, s.Width, s.WEB, s.Area, s.Flange, s.SteelTypesID, s.OriginID, s.GroupBy, s.GroupBySort, s.Weight, s.Radi, s.CBWidth FROM SteelSizes s ORDER BY s.SteelTypesID, s.StrictOrder", "SteelSizes");

        // 3. Origins
        using (var w = new StreamWriter(Path.Combine(outDir, "origins.tsv"), false, Encoding.UTF8))
            ExportTable(src, w, "SELECT OriginID, Origin, Steels FROM Origin ORDER BY OriginID", "Origin");

        // 4. Failure Temps
        using (var w = new StreamWriter(Path.Combine(outDir, "failure_temps.tsv"), false, Encoding.UTF8))
            ExportTable(src, w, "SELECT MajorID, FailureTempDescription, CountryFailureTemp, FailureTempID, masterFTID FROM FailureTemps ORDER BY MajorID", "FailureTemps");

        // 5. Hours (fire ratings)
        using (var w = new StreamWriter(Path.Combine(outDir, "hours.tsv"), false, Encoding.UTF8))
            ExportTable(src, w, "SELECT HourID, Hour_Protection, AbbrevHour_Protection, Abrrev FROM Hours ORDER BY HourID", "Hours");

        // 6. HP Data (section factor profiles)
        using (var w = new StreamWriter(Path.Combine(outDir, "hp_data.tsv"), false, Encoding.UTF8))
            ExportTable(src, w, "SELECT HPName, InternalID, HPDescription, Abbreviation, Faces, Beam_Column, SteelTypesID, HPSided, HPOverABand, HPType, Composite, Board_Section_Only, HPDefault FROM HPData ORDER BY SteelTypesID, InternalID", "HPData");

        // 7. HP Over A (section factor values per steel size per HP profile)
        using (var w = new StreamWriter(Path.Combine(outDir, "hp_over_a.tsv"), false, Encoding.UTF8))
            ExportTable(src, w, "SELECT * FROM HPOverA", "HPOverA");

        // 8. Nullifire Products only (SupplierID=4 is Tremco CPG UK / Nullifire)
        using (var w = new StreamWriter(Path.Combine(outDir, "products.tsv"), false, Encoding.UTF8))
            ExportTable(src, w, "SELECT ProductID, ProductName, ProductTypeID, SupplierID, Density, SolidFactor, Description, Uses, Comments, Catalogue_Band, BaseCoat_Container_One, BaseCoat_Container_Two, BaseCoat_Container_One_KG, BaseCoat_Container_Two_KG, SolventBased, Discontinued, OffSetDFT, FailureTempCanDO, HoursCanDO, BaseCoat_Container_Three, BaseCoat_Container_Three_KG, BaseCoat_Container_Four, BaseCoat_Container_Four_KG FROM LibraryPDetails WHERE SupplierID = 4 ORDER BY ProductName", "Products (Nullifire)");

        // 9. Loadings (DFT data) for Nullifire products only
        using (var w = new StreamWriter(Path.Combine(outDir, "loadings.tsv"), false, Encoding.UTF8))
            ExportTable(src, w, "SELECT l.CoverageDFT, l.CompositeType, l.Hour, l.ProductID, l.FailureTempID, l.MultiFailureTempID, l.CoverageID, l.IncreaseID, l.CompositeHighestDFT FROM Loadings1035 l INNER JOIN LibraryPDetails p ON l.ProductID = p.ProductID WHERE p.SupplierID = 4", "Loadings (Nullifire)");

        // 10. Catalogue (band to HP mapping)
        using (var w = new StreamWriter(Path.Combine(outDir, "catalogue.tsv"), false, Encoding.UTF8))
            ExportTable(src, w, "SELECT [Band], HPName FROM Catalogue ORDER BY [Band], HPName", "Catalogue");

        // 11. Products_Hours (which fire ratings available per product)
        using (var w = new StreamWriter(Path.Combine(outDir, "products_hours.tsv"), false, Encoding.UTF8))
            ExportTable(src, w, "SELECT ph.lookId, ph.LibraryPDetails_ProductID, ph.FailureTempID, ph.SteelTypesID, ph.CountryCodeId FROM Products_Hours ph INNER JOIN LibraryPDetails p ON ph.LibraryPDetails_ProductID = p.ProductID WHERE p.SupplierID = 4", "Products_Hours (Nullifire)");

        // 12. Products_FailureTemps
        using (var w = new StreamWriter(Path.Combine(outDir, "products_failure_temps.tsv"), false, Encoding.UTF8))
            ExportTable(src, w, "SELECT pf.ProductID, pf.UseBand, pf.Hour, pf.CountryCodeId, pf.lookId FROM Products_FailureTemps pf INNER JOIN LibraryPDetails p ON pf.ProductID = p.ProductID WHERE p.SupplierID = 4", "Products_FailureTemps (Nullifire)");

        // 13. Topseals
        using (var w = new StreamWriter(Path.Combine(outDir, "topseals.tsv"), false, Encoding.UTF8))
            ExportTable(src, w, "SELECT * FROM Topseals", "Topseals");

        // 14. Supplier info for Nullifire
        using (var w = new StreamWriter(Path.Combine(outDir, "supplier.tsv"), false, Encoding.UTF8))
            ExportTable(src, w, "SELECT * FROM SData WHERE SupplierID = 4", "Supplier");

        // 15. Bands (section factor ranges)
        using (var w = new StreamWriter(Path.Combine(outDir, "bands.tsv"), false, Encoding.UTF8))
            ExportTable(src, w, "SELECT * FROM Bands1035", "Bands1035");

        // 16. ProdType
        using (var w = new StreamWriter(Path.Combine(outDir, "prod_types.tsv"), false, Encoding.UTF8))
            ExportTable(src, w, "SELECT * FROM ProdType", "ProdType");

        Console.WriteLine("\nDone! TSV files exported.");
    }
}
'''
    # Write and compile
    os.makedirs("data/tsv", exist_ok=True)
    cs_path = "data/exporter.cs"
    with open(cs_path, "w") as f:
        f.write(cs_code)

    csproj = '''<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net472</TargetFramework>
    <PlatformTarget>x86</PlatformTarget>
    <LangVersion>8.0</LangVersion>
  </PropertyGroup>
</Project>'''
    with open("data/exporter.csproj", "w") as f:
        f.write(csproj)

    print("Building exporter...")
    os.system("cd data && dotnet build -v q exporter.csproj 2>&1")
    print("Running exporter...")
    tsv_dir = os.path.abspath("data/tsv")
    os.system(f'cd data && dotnet run --project exporter.csproj -- "{tsv_dir}" 2>&1')
    return tsv_dir


def build_sqlite(tsv_dir):
    """Convert TSV exports into a clean SQLite database."""
    db_path = "data/nullifire.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Schema
    c.executescript('''
        CREATE TABLE steel_types (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            abbrev TEXT NOT NULL,
            coverage_band TEXT,
            sort_order INTEGER
        );

        CREATE TABLE origins (
            id INTEGER PRIMARY KEY,
            code TEXT NOT NULL,
            description TEXT
        );

        CREATE TABLE steel_sections (
            id INTEGER PRIMARY KEY,
            serial_size TEXT NOT NULL,
            depth REAL,
            width REAL,
            web_thickness REAL,
            area REAL,
            flange_thickness REAL,
            steel_type_id INTEGER REFERENCES steel_types(id),
            origin_id INTEGER REFERENCES origins(id),
            group_name TEXT,
            group_sort REAL,
            weight REAL,
            root_radius REAL,
            cb_width REAL
        );

        CREATE TABLE failure_temps (
            id INTEGER PRIMARY KEY,
            description TEXT NOT NULL,
            is_country_specific INTEGER,
            temp_id INTEGER,
            master_ft_id INTEGER
        );

        CREATE TABLE fire_ratings (
            id INTEGER PRIMARY KEY,
            description TEXT NOT NULL,
            abbrev TEXT,
            short_abbrev TEXT
        );

        CREATE TABLE hp_profiles (
            name TEXT PRIMARY KEY,
            internal_id INTEGER,
            description TEXT,
            abbreviation TEXT,
            faces INTEGER,
            beam_column INTEGER,
            steel_type_id INTEGER REFERENCES steel_types(id),
            sided TEXT,
            hp_over_a_band TEXT,
            hp_type TEXT,
            is_composite INTEGER,
            board_only INTEGER,
            default_profile TEXT
        );

        CREATE TABLE section_factors (
            steel_section_id INTEGER REFERENCES steel_sections(id),
            hp_profile_name TEXT REFERENCES hp_profiles(name),
            hp_over_a REAL,
            PRIMARY KEY (steel_section_id, hp_profile_name)
        );

        CREATE TABLE products (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            product_type_id INTEGER,
            supplier_id INTEGER,
            density REAL,
            solid_factor REAL,
            description TEXT,
            uses TEXT,
            comments TEXT,
            catalogue_band TEXT,
            container_1_litres REAL,
            container_2_litres REAL,
            container_1_kg REAL,
            container_2_kg REAL,
            is_solvent_based INTEGER,
            is_discontinued INTEGER,
            offset_dft REAL,
            available_temps TEXT,
            available_hours TEXT,
            container_3_litres REAL,
            container_3_kg REAL,
            container_4_litres REAL,
            container_4_kg REAL
        );

        CREATE TABLE dft_data (
            product_id INTEGER REFERENCES products(id),
            failure_temp_id INTEGER REFERENCES failure_temps(id),
            fire_rating_id INTEGER REFERENCES fire_ratings(id),
            coverage_id INTEGER,
            dft_mm REAL NOT NULL,
            composite_type INTEGER,
            multi_ft_id INTEGER,
            increase_id INTEGER,
            composite_highest_dft REAL
        );

        CREATE TABLE catalogue (
            band TEXT,
            hp_name TEXT REFERENCES hp_profiles(name)
        );

        CREATE TABLE product_hours (
            product_id INTEGER REFERENCES products(id),
            failure_temp_id INTEGER,
            steel_type_id INTEGER REFERENCES steel_types(id),
            look_id INTEGER
        );

        CREATE TABLE product_failure_temps (
            product_id INTEGER REFERENCES products(id),
            use_band TEXT,
            hour INTEGER,
            look_id INTEGER
        );

        CREATE TABLE topseals (
            id INTEGER PRIMARY KEY,
            name TEXT
        );

        CREATE TABLE prod_types (
            id INTEGER PRIMARY KEY,
            name TEXT,
            uses_kg INTEGER,
            uses_litres INTEGER,
            uses_sqm INTEGER,
            calc_band TEXT,
            show_dft INTEGER,
            show_topseal INTEGER
        );

        CREATE TABLE bands (
            band_id TEXT,
            hp_over_a REAL,
            coverage_id INTEGER
        );

        -- Indexes for fast lookup
        CREATE INDEX idx_sections_type ON steel_sections(steel_type_id);
        CREATE INDEX idx_sections_origin ON steel_sections(origin_id);
        CREATE INDEX idx_sections_serial ON steel_sections(serial_size);
        CREATE INDEX idx_dft_product ON dft_data(product_id);
        CREATE INDEX idx_dft_lookup ON dft_data(product_id, failure_temp_id, fire_rating_id, coverage_id);
        CREATE INDEX idx_sf_section ON section_factors(steel_section_id);
        CREATE INDEX idx_bands_coverage ON bands(coverage_id);
        CREATE INDEX idx_bands_hpa ON bands(band_id, hp_over_a);
    ''')

    def read_tsv(filename):
        path = os.path.join(tsv_dir, filename)
        if not os.path.exists(path):
            print(f"  WARNING: {filename} not found")
            return [], []
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        if not lines:
            return [], []
        headers = lines[0].strip().split("\t")
        rows = []
        for line in lines[1:]:
            vals = line.strip().split("\t")
            # Pad short rows
            while len(vals) < len(headers):
                vals.append("")
            rows.append(vals)
        return headers, rows

    def safe_float(v):
        try:
            return float(v) if v.strip() else None
        except:
            return None

    def safe_int(v):
        try:
            return int(float(v)) if v.strip() else None
        except:
            return None

    def safe_bool(v):
        return 1 if v.strip().lower() in ("true", "1", "yes") else 0

    # Import steel types
    _, rows = read_tsv("steel_types.tsv")
    for r in rows:
        c.execute("INSERT INTO steel_types VALUES (?,?,?,?,?)",
                  (safe_int(r[0]), r[1], r[2], r[3], safe_int(r[4])))
    print(f"  steel_types: {len(rows)}")

    # Import origins
    _, rows = read_tsv("origins.tsv")
    for r in rows:
        c.execute("INSERT INTO origins VALUES (?,?,?)",
                  (safe_int(r[0]), r[1], r[2]))
    print(f"  origins: {len(rows)}")

    # Import steel sections
    _, rows = read_tsv("steel_sizes.tsv")
    for r in rows:
        c.execute("INSERT INTO steel_sections VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  (safe_int(r[0]), r[1], safe_float(r[2]), safe_float(r[3]),
                   safe_float(r[4]), safe_float(r[5]), safe_float(r[6]),
                   safe_int(r[7]), safe_int(r[8]), r[9], safe_float(r[10]),
                   safe_float(r[11]), safe_float(r[12]), safe_float(r[13])))
    print(f"  steel_sections: {len(rows)}")

    # Import failure temps
    _, rows = read_tsv("failure_temps.tsv")
    for r in rows:
        c.execute("INSERT INTO failure_temps VALUES (?,?,?,?,?)",
                  (safe_int(r[0]), r[1], safe_bool(r[2]), safe_int(r[3]), safe_int(r[4])))
    print(f"  failure_temps: {len(rows)}")

    # Import fire ratings
    _, rows = read_tsv("hours.tsv")
    for r in rows:
        c.execute("INSERT INTO fire_ratings VALUES (?,?,?,?)",
                  (safe_int(r[0]), r[1], r[2], r[3]))
    print(f"  fire_ratings: {len(rows)}")

    # Import HP profiles
    _, rows = read_tsv("hp_data.tsv")
    for r in rows:
        c.execute("INSERT INTO hp_profiles VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  (r[0], safe_int(r[1]), r[2], r[3], safe_int(r[4]),
                   safe_bool(r[5]), safe_int(r[6]), r[7], r[8], r[9],
                   safe_bool(r[10]), safe_bool(r[11]), r[12]))
    print(f"  hp_profiles: {len(rows)}")

    # Import HP Over A (section factors)
    headers, rows = read_tsv("hp_over_a.tsv")
    if headers:
        # HPOverA table has columns: SteelSizesID, then one column per HP profile
        hp_cols = headers[1:]  # Skip SteelSizesID
        count = 0
        for r in rows:
            section_id = safe_int(r[0])
            if section_id is None:
                continue
            for i, hp_name in enumerate(hp_cols):
                val = safe_float(r[i + 1]) if i + 1 < len(r) else None
                if val is not None and val > 0:
                    c.execute("INSERT OR IGNORE INTO section_factors VALUES (?,?,?)",
                              (section_id, hp_name, val))
                    count += 1
        print(f"  section_factors: {count}")

    # Import products
    _, rows = read_tsv("products.tsv")
    for r in rows:
        c.execute("INSERT INTO products VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  (safe_int(r[0]), r[1], safe_int(r[2]), safe_int(r[3]),
                   safe_float(r[4]), safe_float(r[5]), r[6], r[7], r[8], r[9],
                   safe_float(r[10]), safe_float(r[11]), safe_float(r[12]),
                   safe_float(r[13]), safe_bool(r[14]), safe_bool(r[15]),
                   safe_float(r[16]), r[17], r[18],
                   safe_float(r[19]), safe_float(r[20]),
                   safe_float(r[21]), safe_float(r[22])))
    print(f"  products: {len(rows)}")

    # Import DFT data (loadings)
    _, rows = read_tsv("loadings.tsv")
    for r in rows:
        c.execute("INSERT INTO dft_data VALUES (?,?,?,?,?,?,?,?,?)",
                  (safe_int(r[3]), safe_int(r[4]), safe_int(r[2]), safe_int(r[6]),
                   safe_float(r[0]), safe_int(r[1]), safe_int(r[5]),
                   safe_int(r[7]), safe_float(r[8])))
    print(f"  dft_data: {len(rows)}")

    # Import catalogue
    _, rows = read_tsv("catalogue.tsv")
    for r in rows:
        c.execute("INSERT INTO catalogue VALUES (?,?)", (r[0], r[1]))
    print(f"  catalogue: {len(rows)}")

    # Import product hours
    _, rows = read_tsv("products_hours.tsv")
    for r in rows:
        c.execute("INSERT INTO product_hours VALUES (?,?,?,?)",
                  (safe_int(r[1]), safe_int(r[2]), safe_int(r[3]), safe_int(r[0])))
    print(f"  product_hours: {len(rows)}")

    # Import product failure temps
    _, rows = read_tsv("products_failure_temps.tsv")
    for r in rows:
        c.execute("INSERT INTO product_failure_temps VALUES (?,?,?,?)",
                  (safe_int(r[0]), r[1], safe_int(r[2]), safe_int(r[4])))
    print(f"  product_failure_temps: {len(rows)}")

    # Import topseals
    headers, rows = read_tsv("topseals.tsv")
    if headers and rows:
        for r in rows:
            c.execute("INSERT OR IGNORE INTO topseals VALUES (?,?)",
                      (safe_int(r[0]), r[1] if len(r) > 1 else ""))
    print(f"  topseals: {len(rows)}")

    # Import prod types
    _, rows = read_tsv("prod_types.tsv")
    for r in rows:
        c.execute("INSERT INTO prod_types VALUES (?,?,?,?,?,?,?,?)",
                  (safe_int(r[11]), r[0], safe_bool(r[2]), safe_bool(r[3]),
                   safe_bool(r[4]), r[5], safe_bool(r[8]), safe_bool(r[10])))
    print(f"  prod_types: {len(rows)}")

    # Import bands
    _, rows = read_tsv("bands.tsv")
    if rows:
        for r in rows:
            c.execute("INSERT INTO bands VALUES (?,?,?)",
                      (r[0] if r[0] else None, safe_float(r[1]) if len(r) > 1 else None,
                       safe_int(r[2]) if len(r) > 2 else None))
    print(f"  bands: {len(rows)}")

    conn.commit()

    # Verify
    c.execute("SELECT COUNT(*) FROM products")
    print(f"\nVerification:")
    print(f"  Products: {c.fetchone()[0]}")
    c.execute("SELECT COUNT(*) FROM dft_data")
    print(f"  DFT records: {c.fetchone()[0]}")
    c.execute("SELECT COUNT(*) FROM steel_sections")
    print(f"  Steel sections: {c.fetchone()[0]}")
    c.execute("SELECT COUNT(*) FROM section_factors")
    print(f"  Section factors: {c.fetchone()[0]}")
    c.execute("SELECT name FROM products ORDER BY name")
    print(f"  Nullifire products:")
    for row in c.fetchall():
        print(f"    - {row[0]}")

    conn.close()
    print(f"\nDatabase saved to: {os.path.abspath(db_path)}")


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    tsv_dir = export_via_csharp()
    print("\n--- Building SQLite database ---")
    build_sqlite(tsv_dir)
