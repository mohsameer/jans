/*
 * Copyright [2024] [Janssen Project]
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 * 
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package io.jans.lock.service.ws.rs.audit;

import io.jans.lock.service.util.AuthUtil;
import io.jans.lock.service.util.ServerUtil;
import io.jans.model.net.HttpServiceResponse;

import jakarta.enterprise.context.Dependent;
import jakarta.inject.Inject;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.core.Response;
import jakarta.ws.rs.core.SecurityContext;

import org.apache.commons.io.IOUtils;
import org.json.JSONObject;
import org.slf4j.Logger;

/**
 * Provides interface for audit REST web services
 *
 * @author Yuriy Movchan Date: 06/06/2024
 */
@Dependent
@Path("/audit")
public class AuditRestWebServiceImpl implements AuditRestWebService {

    @Inject
    private Logger log;

    @Inject
    AuthUtil authUtil;

    @Override
    public Response processHealthRequest(HttpServletRequest request, HttpServletResponse response,
            SecurityContext sec) {
        log.debug("Processing Health request");
        Response.ResponseBuilder builder = Response.ok();

        builder.cacheControl(ServerUtil.cacheControlWithNoStoreTransformAndPrivate());
        builder.header(ServerUtil.PRAGMA, ServerUtil.NO_CACHE);
        builder.entity("{\"res\" : \"ok\"}");

        return builder.build();
    }

    @Override
    public Response processLogRequest(HttpServletRequest request, HttpServletResponse response, SecurityContext sec) {
        log.debug("Processing Log request - request:{}", request);
        Response.ResponseBuilder builder = Response.ok();
        builder.cacheControl(ServerUtil.cacheControlWithNoStoreTransformAndPrivate());
        builder.header(ServerUtil.PRAGMA, ServerUtil.NO_CACHE);
        builder.entity("{\"res\" : \"ok\"}");
        return builder.build();

    }

    @Override
    public Response processTelemetryRequest(HttpServletRequest request, HttpServletResponse response,
            SecurityContext sec) {
        log.error("Processing Telemetry request - request:{}", request);

        JSONObject json = this.authUtil.getJSONObject(request);
        HttpServiceResponse serviceResponse = this.authUtil.postData("telemetry", json.toString());
        log.error("serviceResponse:{}", serviceResponse);
        String str = authUtil.getResponseEntityString(serviceResponse);
        log.error("Processing Telemetry response - str:{}", str);
        return Response.status(Response.Status.CREATED).entity(str).build();

    }

}
