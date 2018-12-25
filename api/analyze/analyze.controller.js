const AnalyzeService = require('../../core/analyzer/analyzer.service')

class AnalyzeController {
  static get(req, res, next) {
    res.end('hello')
  }

  static async analyze(req, res, next) {
    const {link} = req.body

    console.log(link)

    if(!link)
      res.status(300).json({message: 'LINK IS EMPTY'})
    try {
      const result = await AnalyzeService.analyzeLink(link)
      res.status(200).json({result: result.data})
    } catch (error) {
      res.status(500).json({code: 999, message: error})
    }
  }
}

module.exports = AnalyzeController