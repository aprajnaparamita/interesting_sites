#!/usr/bin/env ruby

require 'json'

count = 0
missing = []
had = []
Dir['extracted_text/*.json'].each do |file|
  data = JSON.parse(File.read(file))
  audio = data["audio_transcript"] if data and data.is_a? Hash
  if audio and audio != ""
    had.push file
  else
    missing.push file
    count += 1
  end
  puts "#{file}: #{audio}"
end

puts "Missing:#{count}"
missing.each do |file|
  puts file
end
