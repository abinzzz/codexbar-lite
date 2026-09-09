// Generate README demos from the production renderer without accessing account data.
// Usage: swift tools/generate-demo.swift PATH_TO_RENDERER OUTPUT_DIRECTORY
import AppKit
import ImageIO
import UniformTypeIdentifiers

let args = CommandLine.arguments
guard args.count == 3 else {
    fputs("Usage: generate-demo PATH_TO_RENDERER OUTPUT_DIRECTORY\n", stderr)
    exit(1)
}
let renderer = URL(fileURLWithPath: args[1]).absoluteURL.standardizedFileURL
let output = URL(fileURLWithPath: args[2], isDirectory: true).absoluteURL.standardizedFileURL
try FileManager.default.createDirectory(at: output, withIntermediateDirectories: true)
let width = 288, height = 114
for appearance in ["Light", "Dark"] {
    let target = output.appendingPathComponent("demo-\(appearance.lowercased()).gif")
    guard let destination = CGImageDestinationCreateWithURL(target as CFURL, UTType.gif.identifier as CFString, 101, nil) else {
        fatalError("Cannot create GIF")
    }
    CGImageDestinationSetProperties(destination, [kCGImagePropertyGIFDictionary: [kCGImagePropertyGIFLoopCount: 0]] as CFDictionary)
    for step in 0...100 {
        let primary = 100 - step
        let secondary = 100 - Int((Double(step) * 0.15).rounded())
        let process = Process()
        process.executableURL = renderer
        process.arguments = [appearance]
        let input = Pipe(), result = Pipe()
        process.standardInput = input
        process.standardOutput = result
        try process.run()
        let rows: [[String: Any]] = [["label": "5h", "percent": primary], ["label": "7d", "percent": secondary]]
        input.fileHandleForWriting.write(try JSONSerialization.data(withJSONObject: rows))
        try input.fileHandleForWriting.close()
        let data = result.fileHandleForReading.readDataToEndOfFile()
        process.waitUntilExit()
        guard process.terminationStatus == 0,
              let encoded = String(data: data, encoding: .utf8),
              let png = Data(base64Encoded: encoded.trimmingCharacters(in: .whitespacesAndNewlines)),
              let source = CGImageSourceCreateWithData(png as CFData, nil),
              let image = CGImageSourceCreateImageAtIndex(source, 0, nil),
              let context = CGContext(data: nil, width: width, height: height, bitsPerComponent: 8,
                  bytesPerRow: width * 4, space: CGColorSpaceCreateDeviceRGB(),
                  bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue) else {
            fatalError("Renderer failed")
        }
        // An opaque background preserves antialiased text in the GIF palette.
        let color = appearance == "Dark" ? CGColor(red: 13/255, green: 17/255, blue: 23/255, alpha: 1) : CGColor(gray: 1, alpha: 1)
        context.setFillColor(color)
        context.fill(CGRect(x: 0, y: 0, width: width, height: height))
        context.draw(image, in: CGRect(x: 24, y: 24, width: 240, height: 66))
        let delay = step == 0 ? 1.0 : (step == 100 ? 1.6 : 0.08)
        let properties: [CFString: Any] = [kCGImagePropertyGIFDictionary: [
            kCGImagePropertyGIFDelayTime: delay,
            kCGImagePropertyGIFUnclampedDelayTime: delay
        ]]
        CGImageDestinationAddImage(destination, context.makeImage()!, properties as CFDictionary)
    }
    guard CGImageDestinationFinalize(destination) else { fatalError("Cannot write GIF") }
    print("Generated \(target.lastPathComponent): 101 frames, 5h 100→0%, 7d 100→85%")
}
