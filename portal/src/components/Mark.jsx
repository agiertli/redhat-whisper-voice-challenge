// The Whisper status ring: Red Hat fedora between two sound waves.
// Same artwork as the VAD indicator in src/templates/index.html.
export default function Mark({ state = 'brand', className = '' }) {
  const brand = state === 'brand'
  const cls = brand ? '' : `ind ${state}`
  const red = brand ? '#ee0000' : undefined
  const grey = brand ? '#151515' : undefined
  return (
    <svg className={`${cls} ${className}`} viewBox="0 0 100 100" aria-hidden="true">
      <circle className="ring-circle" cx="50" cy="50" r="47" fill="none" stroke={red} strokeWidth="1.5" strokeDasharray="2 3" opacity="0.7" />
      <g>
        <rect className="wave-bar" fill={grey} x="4" y="42" width="2" height="16" rx="0.5" opacity="0.5" />
        <rect className="wave-bar" fill={grey} x="8" y="34" width="2" height="32" rx="0.5" opacity="0.7" />
        <rect className="wave-bar" fill={grey} x="12" y="26" width="2" height="48" rx="0.5" opacity="0.9" />
        <rect className="wave-bar" fill={grey} x="16" y="38" width="2" height="24" rx="0.5" />
        <rect className="wave-bar" fill={grey} x="20" y="30" width="2" height="40" rx="0.5" />
      </g>
      <g transform="translate(26, 31.9) scale(0.25)">
        <path className="hat-shadow" d="M157.77,62.61a14,14,0,0,1,.31,3.42c0,14.88-18.1,17.46-30.61,17.46C78.830,83.49,42.53,53.26,42.53,44a6.430,6.430,0,0,1,.22-1.94l-3.66,9.06a18.450,18.450,0,0,0-1.51,7.33c0,18.11,41,45.48,87.74,45.48,20.69,0,36.43-7.76,36.43-21.77,0-1.08,0-1.94-1.73-10.13Z" fill={brand ? '#000' : undefined} opacity={brand ? 1 : undefined} />
        <path className="hat-red" fill={red} d="M127.47,83.49c12.51,0,30.61-2.58,30.61-17.46a14,14,0,0,0-.31-3.42l-7.45-32.36c-1.72-7.12-3.23-10.35-15.73-16.6C124.89,8.69,103.76.5,97.51.5,91.69.5,90,8,83.06,8c-6.680,0-11.64-5.6-17.89-5.6-6,0-9.91,4.090-12.93,12.5,0,0-8.410,23.72-9.490,27.16A6.430,6.430,0,0,0,42.53,44c0,9.220,36.3,39.45,84.94,39.45M160,72.07c1.73,8.19,1.73,9.05,1.73,10.13,0,14-15.740,21.77-36.430,21.77C78.540,104,37.580,76.6,37.580,58.49a18.450,18.450,0,0,1,1.510-7.33C22.270,52,.5,55,.5,74.220c0,31.480,74.590,70.280,133.650,70.280,45.280,0,56.700-20.480,56.700-36.650,0-12.720-11-27.160-30.830-35.780" />
      </g>
      <g>
        <rect className="wave-bar" fill={grey} x="78" y="30" width="2" height="40" rx="0.5" />
        <rect className="wave-bar" fill={grey} x="82" y="38" width="2" height="24" rx="0.5" />
        <rect className="wave-bar" fill={grey} x="86" y="26" width="2" height="48" rx="0.5" opacity="0.9" />
        <rect className="wave-bar" fill={grey} x="90" y="34" width="2" height="32" rx="0.5" opacity="0.7" />
        <rect className="wave-bar" fill={grey} x="94" y="42" width="2" height="16" rx="0.5" opacity="0.5" />
      </g>
    </svg>
  )
}
