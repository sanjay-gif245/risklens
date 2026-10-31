import { cellColor, strongestPair } from '../lib/correlation'
import { formatNumber } from '../lib/format'

interface CorrelationHeatmapProps {
  tickers: string[]
  matrix: number[][]
}

export function CorrelationHeatmap({ tickers, matrix }: CorrelationHeatmapProps) {
  const pair = strongestPair(tickers, matrix)
  const showValues = tickers.length <= 14
  return (
    <figure className="chart">
      <div className="table-wrap">
        <table className="heatmap">
          <caption className="visually-hidden">Pairwise correlation of daily returns</caption>
          <thead>
            <tr>
              <th scope="col" />
              {tickers.map((t) => (
                <th key={t} scope="col" className="ticker">
                  {t}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {matrix.map((row, i) => (
              <tr key={tickers[i]}>
                <th scope="row" className="ticker">
                  {tickers[i]}
                </th>
                {row.map((value, j) => (
                  <td
                    key={tickers[j]}
                    style={{
                      background: i === j ? 'var(--surface-raised)' : cellColor(value),
                      color: i !== j && Math.abs(value) > 0.65 ? '#0b0f0e' : undefined,
                    }}
                    title={`${tickers[i]} / ${tickers[j]}: ${formatNumber(value)}`}
                  >
                    {showValues ? (
                      formatNumber(value)
                    ) : (
                      <span className="visually-hidden">{formatNumber(value)}</span>
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <figcaption className="chart__caption">
        {pair
          ? `Correlation of daily returns. The most closely linked pair is ${pair.a} and ${pair.b} at ${formatNumber(pair.value)}. In a market sell-off correlations tend to rise toward 1, so diversification is weakest when it is needed most.`
          : 'A single holding has nothing to be correlated with.'}
      </figcaption>
    </figure>
  )
}
