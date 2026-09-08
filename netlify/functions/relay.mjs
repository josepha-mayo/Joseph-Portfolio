import {handleMcp} from '../../src/mcp.mjs';
export default async function(request){return handleMcp(request)}
export const config={path:'/mcp'};
