import AppKit

struct Row: Decodable {
    let label: String
    let percent: Int?
}
func fail() -> Never { fputs("Invalid renderer input\n", stderr); exit(1) }
guard CommandLine.arguments.count == 2,
      let rows = try? JSONDecoder().decode([Row].self, from: FileHandle.standardInput.readDataToEndOfFile()),
      rows.count == 2,
      rows.allSatisfy({ $0.label.count <= 12 && ($0.percent == nil || (0...100).contains($0.percent!)) }) else { fail() }
let dark = CommandLine.arguments[1].lowercased() == "dark"
let width = 80, height = 22, scale = 3
guard let bitmap = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: width * scale, pixelsHigh: height * scale,
    bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB,
    bytesPerRow: 0, bitsPerPixel: 0), let context = NSGraphicsContext(bitmapImageRep: bitmap) else { fail() }
NSGraphicsContext.saveGraphicsState()
NSGraphicsContext.current = context
context.cgContext.clear(CGRect(x: 0, y: 0, width: width * scale, height: height * scale))
context.cgContext.scaleBy(x: CGFloat(scale), y: CGFloat(scale))
let foreground = dark ? NSColor.white : NSColor.black
for (index, row) in rows.enumerated() {
    let y = CGFloat(index == 0 ? 11 : 0)
    let text = row.label as NSString
    var fontSize: CGFloat = 10
    while text.size(withAttributes: [.font: NSFont.systemFont(ofSize: fontSize, weight: .medium)]).width > 21 && fontSize > 6 {
        fontSize -= 0.5
    }
    text.draw(in: NSRect(x: 0, y: y, width: 22, height: 12), withAttributes: [
        .font: NSFont.systemFont(ofSize: fontSize, weight: .medium), .foregroundColor: foreground])
    let percentText = (row.percent.map { "\($0)%" } ?? "--%") as NSString
    let percentFont = NSFont.monospacedDigitSystemFont(ofSize: row.percent == 100 ? 8.5 : 10, weight: .medium)
    percentText.draw(at: NSPoint(x: 55, y: y), withAttributes: [.font: percentFont, .foregroundColor: foreground])
    let percent = row.percent ?? 0
    let filled = percent <= 0 ? 0 : min(5, max(1, Int((Double(percent) / 20).rounded())))
    let accent: NSColor = percent > 60 ? .systemGreen : (percent >= 20 ? .systemOrange : .systemRed)
    for segment in 0..<5 {
        (segment < filled ? accent : (dark ? NSColor.white : NSColor.gray).withAlphaComponent(0.24)).setFill()
        NSBezierPath(roundedRect: NSRect(x: 23 + CGFloat(segment) * 5.2, y: y + 3.2, width: 3.2, height: 5.8),
                     xRadius: 1.6, yRadius: 1.6).fill()
    }
}
NSGraphicsContext.restoreGraphicsState()
bitmap.size = NSSize(width: width, height: height)
guard let png = bitmap.representation(using: .png, properties: [:]) else { fail() }
print(png.base64EncodedString())
