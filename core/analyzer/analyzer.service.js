const path = require('path')
const util = require('util')
const fs = require('fs')
const execFile = util.promisify(require('child_process').execFile);

class AnalyzerServiec {
  static async analyzeLink(link) {
    const analyzePyPath = path.resolve(__dirname, 'analyzer.py')
    let {stderr, stdout} = await execFile('python', [analyzePyPath, '-l', link], {shell: true, cwd: path.resolve(__dirname)})
    if(stderr)
      throw new Error(stderr)
    else {
      stdout = stdout.replace(/\r?\n|\r/g,"")
      const outputFilePath = path.resolve(__dirname,stdout)

      const outputFileData = fs.readFileSync(outputFilePath).toString()
      return {data: outputFileData}
    }
  }
}

module.exports = AnalyzerServiec