import { execSync } from "child_process";
import { mkdirSync } from "fs";

// ensure output directory exists
mkdirSync("./src/grpc", { recursive: true });

const command = `
npx grpc_tools_node_protoc \
  --plugin=protoc-gen-ts=node_modules/.bin/protoc-gen-ts \
  --ts_out=grpc_js:./src/grpc \
  --js_out=import_style=commonjs,binary:./src/grpc \
  --grpc_out=grpc_js:./src/grpc \
  --proto_path=../protos \
  ../protos/*.proto
`;

execSync(command, { stdio: "inherit" });
