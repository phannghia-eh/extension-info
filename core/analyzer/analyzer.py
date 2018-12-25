#!/usr/bin/python3


from GLib import *
import time


def main():
    parser = argparse.ArgumentParser(prog='analyzer.py')
    parser.add_argument("-l", "--link",help="Link",required=False)
    parser.add_argument("-i", "--id",help="ID",required=False)
    parser.add_argument("-n", "--name",help="Name",required=False)
    parser.add_argument("-a", "--all",help="All",required=False)
    args = parser.parse_args()
    if args.link:
        ID, Ext = GetExtID(args.link)
        Extdir = DownloadAndExtractExt(ID, Ext)
        if "Already" == Extdir:
            GetReport(ID)
        elif "Error" != Extdir:
            ExtensionAnalyzer(ID, Extdir)
            GetReport(ID)
    elif args.all:
        for ID, Ext in GetListExt(database):
            ExtensionAnalyzer(ID, Ext)
        GenReport("Output")
    elif args.id:
        result = SearchByID(args.id)
    elif args.name:
        result = SearchByName(args.name)


if __name__ == "__main__":
    main()
