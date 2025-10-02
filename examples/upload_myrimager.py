import json
import os
import re
import winreg
import ContractionDB

def upload_foc_file(config_file, fname=None):
    # Load DB config
    try:
        loginData = json.load(open(config_file))
        db = ContractionDB(**loginData)
    except:
        raise Exception(f"Failed to connect to DB, check Config File >{config_file}<")

    file_list = []

    if fname:
        file_list.append(fname)
    else:
        # fallback to environment var FOC_OUTFILE
        reg_key = "FOC_OUTFILE"
        hkey = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment")
        fname, _ = winreg.QueryValueEx(hkey, reg_key)
        if os.path.isfile(fname):
            file_list.append(fname)
        else:
            raise Exception(f"Env {reg_key} does not contain valid file >{fname}<")

    for f in file_list:
        if re.search(r".xml$", f):
            f = re.sub(r"\.xml$", ".csv", f)
            print(f"Converting XML -> {f}")

        if os.path.isfile(f):
            print(f"Uploading {f}")
            try:
                id_mea = db.upload_traces_from_csv(f)
                traces = db.get_id_traces(id_mea)
                for t in traces:
                    db.add_trace(t)
                    t.filter_min_max()
                    t.find_peaks()
                    db.add_stats_to_trace(t)
                    db.remove_peaks_from_trace(t)
                    db.add_peaks_to_trace(t)
            except Exception as e:
                raise Exception(f"Could not upload or process file {f}: {e}")
        else:
            print(f"No file >{f}< found")

    db.commit()
    db.close()
    print("Upload DONE")
