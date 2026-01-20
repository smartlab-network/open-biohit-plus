

def main():
    import json
    import sys
    print(f"name of package {__name__}")
    print(f"file  {__file__}")

    sys.path.append(r"E:\Labhub\Repos\smartlab-network\contractiondb-python\src")
    from contractiondb import ContractionDB
    from contractiondb.regex import parse_args
    from matplotlib import pyplot as plt

    print(__name__)

    args=parse_args()

    print(f"config is {args.config}")

    loginData=json.load(open(args.config))
    db = ContractionDB(**loginData)

    #traces = db.get_traces(exp=args.expName, mea=args.meaName, well=args.wellName)
    traces = db.get_trace_ids(args.expName, args.meaName, args.wellName, start_date='2025-01-01')

    # plot them
    for t in traces:
        db.add_trace(t)
        t.filter_min_max()
        t.find_peaks()
        graph = plt.plot(t.time, t.raw_distance)
        t.plot()
        db.remove_peaks_from_trace(t)
        db.add_peaks_to_trace(t)

    print('done')

if __name__ == "__main__":
    # Nur beim direkten Ausführen ausführen
    import sys
    main()