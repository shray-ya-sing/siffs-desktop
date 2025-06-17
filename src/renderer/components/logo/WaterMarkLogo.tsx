export default function WatermarkLogo() {
  return (
  <svg
    width="400"
    height="400"
    viewBox="0 0 512 512"
    className="absolute inset-0 m-auto opacity-[0.02]"
    style={{ zIndex: 0 }}
  >
    <defs>
      <linearGradient
        id="watermark-grad1"
        x1="265.13162"
        y1="152.08855"
        x2="456.58057"
        y2="295.04551"
        gradientUnits="userSpaceOnUse"
      >
        <stop style={{ stopColor: "#ffffff", stopOpacity: 1 }} offset="0" />
        <stop style={{ stopColor: "#ffffff", stopOpacity: 0 }} offset="1" />
      </linearGradient>
      <linearGradient
        id="watermark-grad2"
        x1="59.827798"
        y1="254.1107"
        x2="185.78105"
        y2="104.22633"
        gradientUnits="userSpaceOnUse"
      >
        <stop style={{ stopColor: "#ffffff", stopOpacity: 1 }} offset="0" />
        <stop style={{ stopColor: "#ffffff", stopOpacity: 0 }} offset="1" />
      </linearGradient>
      <linearGradient
        id="watermark-grad3"
        x1="143.58672"
        y1="213.17589"
        x2="227.9754"
        y2="213.17589"
        gradientUnits="userSpaceOnUse"
      >
        <stop style={{ stopColor: "#ffffff", stopOpacity: 1 }} offset="0" />
        <stop style={{ stopColor: "#ffffff", stopOpacity: 0 }} offset="1" />
      </linearGradient>
      <linearGradient
        id="watermark-grad4"
        x1="59.198033"
        y1="130.67651"
        x2="164.36899"
        y2="130.67651"
        gradientUnits="userSpaceOnUse"
      >
        <stop style={{ stopColor: "#ffffff", stopOpacity: 1 }} offset="0" />
        <stop style={{ stopColor: "#ffffff", stopOpacity: 0 }} offset="1" />
      </linearGradient>
      <linearGradient
        id="watermark-grad5"
        x1="227.9754"
        y1="236.79212"
        x2="371.56212"
        y2="236.79212"
        gradientUnits="userSpaceOnUse"
      >
        <stop style={{ stopColor: "#f9f9f9", stopOpacity: 1 }} offset="0" />
        <stop style={{ stopColor: "#f9f9f9", stopOpacity: 0 }} offset="1" />
      </linearGradient>
      <linearGradient
        id="watermark-grad6"
        x1="369.67282"
        y1="206.56335"
        x2="455.9508"
        y2="206.56335"
        gradientUnits="userSpaceOnUse"
      >
        <stop style={{ stopColor: "#ffffff", stopOpacity: 1 }} offset="0" />
        <stop style={{ stopColor: "#ffffff", stopOpacity: 0 }} offset="1" />
      </linearGradient>
    </defs>

    <path
      style={{ fill: "url(#watermark-grad2)", fillOpacity: 1 }}
      d="M 204.67405,379.74908 227.34563,294.73063 144.21648,151.14391 59.827798,128.47232 Z"
    />
    <path
      style={{ fill: "url(#watermark-grad1)", fillOpacity: 1 }}
      d="m 226.77254,295.04551 143.94569,-84.0738 85.86234,22.92922 -252.53629,145.21838 z"
    />
    <path
      style={{ fill: "url(#watermark-grad3)", fillOpacity: 1 }}
      d="M 227.9754,296.61992 V 253.92763 L 165.46527,129.73186 143.58672,151.07801 Z"
    />
    <path
      style={{ fill: "url(#watermark-grad4)", fillOpacity: 1 }}
      d="M 59.198033,128.4045 142.6974,151.77368 164.36899,131.00107 78.320028,109.57934 Z"
    />
    <path style={{ fill: "#333333", fillOpacity: 1 }} d="m 227.34563,295.36039 12.59533,-40.30504" />
    <path
      style={{ fill: "url(#watermark-grad5)", fillOpacity: 1 }}
      d="m 370.30258,179.48339 1.25954,31.48832 -143.58672,83.12915 0.62977,-39.04551 z"
    />
    <path
      style={{ fill: "url(#watermark-grad6)", fillOpacity: 1 }}
      d="m 369.67282,179.48339 86.27798,24.56089 -0.62977,29.59902 -83.75891,-22.67159 z"
    />
  </svg>
)
}
