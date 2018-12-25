import os
import json
import io, re
import sqlite3
from typing import Dict, Any
import logging
import operator
import requests, argparse, zipfile
database = "ExtensionDb.db"
folder = "download"

def FileConcat(file, pattern, string):
    t = ReadFile(file).find(pattern) + len(pattern)
    tmp1 = ReadFile(file)[:t:]
    tmp2 = ReadFile(file)[t::]
    return tmp1 + string + tmp2


def FileConcatReverse(file, pattern, string):
    t = ReadFile(file).rfind(pattern)
    tmp1 = ReadFile(file)[:t:]
    tmp2 = ReadFile(file)[t::]
    return tmp1 + string + tmp2


def StringConcat(src, pattern, string):
    t = src.find(pattern) + len(pattern)
    tmp1 = src[:t:]
    tmp2 = src[t::]
    return tmp1 + string + tmp2


def StringInsert(src, index, string):
    tmp1 = src[:index:]
    tmp2 = src[index::]
    return tmp1 + string + tmp2


def ReadFile(filename):
    with open(filename, "r") as f:
        return f.read()


def ReadLine(filename):
    with open(filename) as f:
        lines = [line.rstrip('\n') for line in f]
        return lines


def ConnectDB(db):
    conn = sqlite3.connect(db)
    return conn


def InserttoDB(conn, cursor, ID, name, path):
    cursor.execute("INSERT INTO Extensions VALUES ('{0}', '{1}', '{2}')".format(ID, name, path))
    conn.commit()


def CloseDB(conn):
    conn.close()


def CheckDownloaded(cursor, ID):
    cursor.execute("SELECT ID FROM Extensions WHERE ID='{0}'".format(ID))
    if cursor.fetchone() == None:
        return False
    return True


def WriteFile(filename, string):
    with open(filename, "w") as f:
        f.write(string)


def CreateDir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)


def GetListExt(db):
    conn = ConnectDB(db)
    cursor = conn.cursor()
    cursor.execute("SELECT ID,Path FROM Extensions")
    ret = cursor.fetchall()
    CloseDB(conn)
    if ret is None:
        return
    return ret


def ListDirTree(path):
    for root, dir, files in os.walk(path):
        level = root.replace(path, '').count(os.sep)
        indent = ' ' * 4 * level
        print('{}{}'.format(indent, os.path.basename(root)))
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            print('{}{}'.format(subindent, f))


def ListJSFile(path):
    files = [val for sublist in
             [[os.path.join(root, js) for js in files if js.endswith('.js')] for root, dir, files in os.walk(path)] for
             val in sublist]
    return files


def ManifestParser(file):
    global name
    with io.open(file, 'r', encoding='utf-8-sig') as f:
        tmpjson = remove_comments(f.read())
        tmpjson = remove_trailing_commas(tmpjson)
        data = json.loads(tmpjson, strict=False)
        if 'name' in data:
            name = data['name']
        permissions = []
        if 'permissions' in data:
            permissions = data['permissions']
        if "content_security_policy" in data:
            csp = data['content_security_policy']
        else:
            csp = "script-src 'self'; object-src 'self'"
        content_scrips = []
        if 'content_scripts' in data:
            for e in data['content_scripts']:
                if e.get('js') is not None:
                    temp = dict(js=e.get('js'), matches=e.get('matches'))
                    content_scrips.append(temp)
    result = dict(name=name, permissions={}, csp=csp, content_scrips=content_scrips)
    with open('permissions.json') as f:
        data = json.load(f)
        for i in permissions:
            if type(i) == str:
                if i in data:
                    temp: Dict[Any, Any] = {i: data[i]}
                    result['permissions'].update(temp)
    return result


def APIParser(file, found):
    with io.open(file, 'r', encoding='utf-8', errors='ignore') as f:
        jsfile = f.read()
    with open('api.json') as f:
        api = json.load(f)
        pattern_list = [key for key, value in api.items()]
    result = {}
    for pattern in pattern_list:
        if pattern in [key for key, value in result.items()] or pattern in found:
            continue
        if "AND" in pattern:
            not_found = False
            cond = pattern.split(" AND ")
            for e in cond:
                if e not in jsfile:
                    not_found = True
                    break
            if not_found:
                continue
            temp: Dict[Any, Any] = {pattern: api[pattern]}
            result.update(temp)
        elif pattern in jsfile:
            temp: Dict[Any, Any] = {pattern: api[pattern]}
            result.update(temp)
    return result


def ValidFilename(value, deletechars):
    for c in deletechars:
        value = value.replace(c, '-')
    return value


def remove_comments(json_like):
    comments_re = re.compile(r'//.*?$|/\*.*?\*/|\'(?:\\.|[^\\\'])*\'|"(?:\\.|[^\\"])*"', re.DOTALL | re.MULTILINE)

    def replacer(match):
        s = match.group(0)
        if s[0] == '/': return ""
        return s

    return comments_re.sub(replacer, json_like)


def remove_trailing_commas(json_like):
    trailing_object_commas_re = re.compile(
        r'(,)\s*}(?=([^"\\]*(\\.|"([^"\\]*\\.)*[^"\\]*"))*[^"]*$)')
    trailing_array_commas_re = re.compile(
        r'(,)\s*\](?=([^"\\]*(\\.|"([^"\\]*\\.)*[^"\\]*"))*[^"]*$)')
    objects_fixed = trailing_object_commas_re.sub("}", json_like)
    objects_fixed = re.sub(";$", ",", objects_fixed)
    # objects_fixed = re.sub(r'\\', r'\\\\', objects_fixed)
    return trailing_array_commas_re.sub("]", objects_fixed)


def ExtensionAnalyzer(ext_id, root_path):
    logging.basicConfig(filename='analyzer.log', level=logging.DEBUG)
    try:
        manifest_file = root_path + "\\manifest.json"
        final_output = {}
        if os.path.exists(manifest_file) and os.path.getsize(manifest_file):
            manifest_output = ManifestParser(manifest_file)
        else:
            manifest_output = dict(permissions={})
        js_files = [e.replace('\\', "\\") for e in ListJSFile(root_path)]
        api_output = dict(api={})
        found = []
        for js in js_files:
            result = APIParser(js, found)
            api_output['api'].update(result)
            found.extend([key for key, value in result.items()])
        final_output.update(manifest_output)
        final_output.update(api_output)
        output_file = 'Output\\' + ValidFilename(ext_id, ":<|>\"/\\?*") + '.json'

        with io.open(output_file, 'w', encoding='utf-8') as f:
            json.dump(final_output, f, ensure_ascii=False)
    except Exception as e:
        log = "\n----------------------\n"
        log += ext_id + ":" + root_path
        logging.exception(log)

def GetReport(id):
    print("Output\\"+ValidFilename(id, ":<|>\"/\\?*")+".json")
def GenReport(json_folder):
    result = dict(perms_avg=0, perms_highest={}, warn_perms_avg=0, top_perms=[], top_warn_perms=[], analyzed_ext=0,
                  above_50=0, above_30=0, above_15=0, below_15=0, etc=0)
    result['perms_highest'] = dict(name=[], quantity=0)
    total_perms = 0
    total_extensions = 0
    total_warn_perms = 0
    total_top_perms = {}
    total_top_warn_perms = {}
    for jsfile in os.listdir(json_folder):
        with io.open("Output\\" + jsfile, 'r', encoding='utf-8', errors='ignore') as f:
            content = json.load(f)
            total_extensions += 1
            perms_quantity = len(content['permissions'])
            total_perms += perms_quantity
            if perms_quantity == result['perms_highest'].get('quantity'):
                result['perms_highest']['name'].append(content['name'])
            elif perms_quantity > result['perms_highest'].get('quantity'):
                result['perms_highest']['name'] = []
                result['perms_highest']['name'].append(content['name'])
                result['perms_highest']['quantity'] = perms_quantity
            for perm, value in content['permissions'].items():
                if value['isWarning'] is True:
                    total_warn_perms += 1
                    if perm in total_top_warn_perms:
                        total_top_warn_perms[perm] += 1
                    else:
                        temp: Dict[Any, Any] = {perm: 1}
                        total_top_warn_perms.update(temp)
                if perm in total_top_perms:
                    total_top_perms[perm] += 1
                else:
                    temp: Dict[Any, Any] = {perm: 1}
                    total_top_perms.update(temp)
            high_risk = 0
            for api, value in content['api'].items():
                if value['risk'] == "High risk":
                    high_risk += 1
            api_quantity = len(content['api'])
            if api_quantity != 0:
                percentage = high_risk / api_quantity
                if percentage >= 0.5:
                    result['above_50'] += 1
                elif percentage >= 0.3:
                    result['above_30'] += 1
                elif percentage >= 0.15:
                    result['above_15'] += 1
                else:
                    result['below_15'] += 1
    result['etc'] = total_extensions - result['above_50'] - result['above_30'] - result['above_15'] - result['below_15']
    result['analyzed_ext'] = total_extensions
    result['perms_avg'] = total_perms // total_extensions
    result['warn_perms_avg'] = total_warn_perms // total_extensions
    count = 0
    for e in sorted(total_top_perms.items(), key=operator.itemgetter(1), reverse=True):
        count += 1
        if count > 10:
            break
        result['top_perms'].append(e)
    count = 0
    for e in sorted(total_top_warn_perms.items(), key=operator.itemgetter(1), reverse=True):
        count += 1
        if count > 10:
            break
        result['top_warn_perms'].append(e)
    with open("Report.json", "w") as f:
        json.dump(result, f)
def SearchByName(keyword):
    keyword = keyword.replace(" ", "-")
    connDB = ConnectDB(database)
    c = connDB.cursor()
    stmt = "SELECT ID,Name,Path FROM Extensions WHERE Name like '%{}%'".format(keyword)
    c.execute(stmt)
    result = c.fetchall()
    CloseDB(connDB)
    if not result:
        return "Extension not found. Please enter link to extension to analyze"
    else:
        result = [(res[0], res[1], "Output\\" + res[0]) for res in result]
        return result


def SearchByID(id):  
    connDB = ConnectDB(database)
    c = connDB.cursor()
    stmt = "SELECT ID,Name,Path FROM Extensions WHERE ID like '%{}%'".format(id)
    c.execute(stmt)
    result = c.fetchall()
    CloseDB(connDB)
    if not result:
        return "Extension not found. Please enter link to extension to analyze"
    else:
        result = [(res[0], res[1], "Output\\" + res[0]) for res in result]
        return result


def GetExtID(arg):
    if arg.startswith('http://'):
        arg = arg.replace('http://', 'https://')
    if arg.startswith('https://'):
        return arg.split('/')[-1:][0], arg.split("/")[-2:][0]
    return arg


def GetCrxUrl(extension_id):
    if '?' in extension_id:
        extension_id = extension_id[:extension_id.find('?')]
    return ('https://clients2.google.com/service/update2/crx?response=redirect&prodversion=49.0'
            '&x=id%3D{extension_id}%26installsource%3Dondemand%26uc'.format(extension_id=extension_id))


def DownloadAndExtractExt(ExtID,ExtName):
    connDB = ConnectDB(database)
    c = connDB.cursor()
    filename = '{0}.crx'.format(ExtName)
    dst_path = folder + "\\" + filename
    dst_dir = folder + "\\" + filename[:-4]
    if CheckDownloaded(c, ExtID):
        return "Already"
    crx_url = GetCrxUrl(ExtID)
    #print ("*" * 20)
    #print ('[+]Downloading {crx_url}'.format(crx_url=crx_url))
    try:
        req = requests.get(crx_url, stream=True)
        status_code = req.status_code
    except Exception as e:
        print ('[!]Couldn\'t request the crx file ({0})'.format(e))
        return "Error"
    if status_code == 200:
        try:
            with open(dst_path, 'wb') as fd:
                for chunk in req.iter_content(chunk_size=128):
                    fd.write(chunk)
        except Exception as e:
            print ('[!]Couldn\'t download the crx file ({0})'.format(e))
            return "Error"
        else:
            """print ('[*]Chrome extension crx file downloaded successfully')
            print ("[*]Save to " + dst_path)"""
            ExtractCRX(filename, dst_path, dst_dir)
            os.remove(dst_path)
            InserttoDB(connDB, c, ExtID, filename[:-4], dst_dir)
            CloseDB(connDB)
            return dst_dir
    else:
        print ('[!]Couldn\'t download the crx file (status code: {0})'.format(status_code))
        return "Error"


def ExtractCRX(filename, path, dst_dir):
    CreateDir(dst_dir)
    #print ('[+]Directory {dir} created'.format(dir=filename[:-4]))
    try:
        #print ('[+]Extracting the contents of {0}...'.format(filename))
        zip_ref = zipfile.ZipFile(path, 'r')
        zip_ref.extractall(dst_dir)
        zip_ref.close()
    except Exception as e:
        print ('[!]Couldn\'t extract the contents of the crx file ({0})'.format(e))
        return False
    else:
        #print ('[*]Extracted successfully')
        return True
